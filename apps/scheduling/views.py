from datetime import datetime, date
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.generics import ListAPIView
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated

from apps.catalog.models import ProcedureType
from apps.clinical.models import PatientClinician
from apps.scheduling.models import Procedure
from apps.scheduling.serializers import (
    ProcedureScheduledPatientSerializer,
    ProcedureSerializer,
)
from apps.scheduling.permissions import IsPatientAdminOrClinician
from apps.scheduling.filters import ProcedureScheduledPatientsFilter
from apps.core.pagination import StandardPagination
from apps.core.permissions_helpers import is_patient_admin, is_clinician
from apps.core.constants import ACTIVE_PROCEDURE_STATUSES


class ProcedureViewSet(viewsets.ModelViewSet):
    """
    Procedures API

    - POST /api/v1/procedures/       (assign procedure to patient)
    - GET /api/v1/procedures/        (list)
    - GET /api/v1/procedures/{id}/   (detail)
    - PATCH/DELETE #TODO
    """

    serializer_class = ProcedureSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticated, IsPatientAdminOrClinician]

    def get_queryset(self):
        """
        Scoping:
        - patient_admin: all procedures
        - clinician: only procedures where they are the clinician
        - others: no access (handled by permission)
        """
        user = self.request.user
        qs = Procedure.objects.select_related(
            "patient", "clinician", "procedure_type"
        ).all()

        if is_clinician(user):
            clinician = user.clinician_profile
            return qs.filter(clinician=clinician)

        return qs.none()

    def perform_create(self, serializer):
        """
        Additional runtime checks:
        - For clinicians:
            * must be linked to patient via active PatientClinician
        - Patient admin can assign any patient/clinician combination (subject to soft-delete / active checks
          handled by serializer and model managers).
        """
        user = self.request.user
        admin = is_patient_admin(user)
        clinician = is_clinician(user)

        patient = serializer.validated_data["patient"]
        clinician_obj = serializer.validated_data["clinician"]

        if clinician and not admin:
            clinician_profile = user.clinician_profile

            has_link = PatientClinician.objects.filter(
                patient=patient,
                clinician=clinician_profile,
                relationship_end__isnull=True,
                deleted_at__isnull=True,
            ).exists()
            if not has_link:
                raise PermissionDenied("You do not have access to this patient.")

        serializer.save()


class ProcedureScheduledPatientsView(ListAPIView):
    """
    GET /api/v1/procedures/scheduled-patients/?procedure_type_id=...

    Lists patients scheduled for a specific procedure type with filtering options.

    - patient_admin: sees all matching procedures
    - clinician: sees only their own procedures (clinician_id filter ignored)
    """

    permission_classes = [IsAuthenticated, IsPatientAdminOrClinician]
    serializer_class = ProcedureScheduledPatientSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProcedureScheduledPatientsFilter
    pagination_class = StandardPagination

    def _parse_and_validate_procedure_type(self, request) -> ProcedureType:
        """
        Validate and parse the required procedure_type_id query parameter.

        Args:
            request: HTTP request object

        Raises:
            ValidationError: if missing or non-integer.
            NotFound: if procedure type does not exist.

        Returns:
            ProcedureType instance
        """
        raw = request.query_params.get("procedure_type_id")
        if raw is None:
            raise ValidationError({"procedure_type_id": ["This field is required."]})

        try:
            type_id = int(raw)
        except (TypeError, ValueError):
            raise ValidationError({"procedure_type_id": ["Must be an integer."]})

        try:
            return ProcedureType.objects.get(pk=type_id)
        except ProcedureType.DoesNotExist:
            raise NotFound("Procedure type not found.")

    def _validate_date_range(self, request) -> None:
        """
        Cross-field validation: date_from must be <= date_to when both present.

        Individual format validation is handled by django-filter's DateFilter.
        Raises:
            ValidationError: if date_from > date_to.
        """
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        if not date_from or not date_to:
            return

        try:
            from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
            to_date = datetime.strptime(date_to, "%Y-%m-%d").date()
        except ValueError:
            # django-filter's DateFilter will handle format errors
            return

        if from_date > to_date:
            raise ValidationError(
                {
                    "non_field_errors": [
                        "date_from must be less than or equal to date_to."
                    ]
                }
            )

    def get_queryset(self):
        """
        Get filtered queryset of procedures for the requested procedure type.

        Validation is done in list() to properly handle exceptions.
        This is called after validation passes, so we can assume
        procedure_type and date_range are valid.

        Returns:
            QuerySet of Procedure objects filtered by type, status, and user role.
        """
        procedure_type = self.request._validated_procedure_type

        user = self.request.user
        admin = is_patient_admin(user)
        clinician = is_clinician(user)

        qs = Procedure.objects.select_related("patient", "clinician").filter(
            procedure_type=procedure_type,
            status__in=Procedure.ACTIVE_PROCEDURE_STATUSES,
            patient__deleted_at__isnull=True,
            clinician__deleted_at__isnull=True,
        )

        if clinician and not admin:
            qs = qs.filter(clinician=user.clinician_profile)

        return qs.order_by("scheduled_at", "id")

    def filter_queryset(self, queryset):
        """
        Override to ignore clinician_id filter for clinicians.

        Clinicians should only see their own procedures, so don't let them
        use clinician_id to try to see other clinicians' procedures.

        Args:
            queryset: The input queryset to filter

        Returns:
            Filtered queryset respecting user role permissions
        """
        user = self.request.user
        clinician = is_clinician(user)
        admin = is_patient_admin(user)

        if clinician and not admin:
            params_dict = self.request.query_params.dict()
            params_dict.pop("clinician_id", None)

            from django.http import QueryDict

            filtered_params = QueryDict(mutable=True)
            filtered_params.update(params_dict)

            filterset = self.filterset_class(
                filtered_params,
                queryset=queryset,
                request=self.request,
            )
            return filterset.qs

        return super().filter_queryset(queryset)

    def list(self, request, *args, **kwargs):
        """
        List scheduled patients for a procedure type.

        Validates required query parameters and then calls parent list().

        Args:
            request: HTTP request object
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Paginated response with scheduled patients
        """
        # Perform validation that should return 400/404 errors
        try:
            procedure_type = self._parse_and_validate_procedure_type(request)
            self._validate_date_range(request)

            # Store validated procedure_type on request for use in get_queryset
            request._validated_procedure_type = procedure_type
        except (ValidationError, NotFound) as e:
            # Re-raise to let DRF's exception handler process it
            raise

        return super().list(request, *args, **kwargs)
