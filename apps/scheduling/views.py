from datetime import datetime, date
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.generics import ListAPIView
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated

from apps.catalog.models import ProcedureType
from apps.clinical.models import PatientClinician
from apps.scheduling.models import Procedure
from apps.scheduling.serializers import ProcedureScheduledPatientSerializer, ProcedureSerializer
from apps.scheduling.permissions import IsPatientAdminOrClinician
from apps.scheduling.filters import ProcedureScheduledPatientsFilter

from rest_framework.exceptions import NotFound, ValidationError


class ProcedurePagination(LimitOffsetPagination):
    default_limit = 20
    max_limit = 100


class ProcedureViewSet(viewsets.ModelViewSet):
    """
    Procedures API

    - POST /api/v1/procedures/       (assign procedure to patient)
    - GET /api/v1/procedures/        (list)
    - GET /api/v1/procedures/{id}/   (detail)
    - PATCH/DELETE #TODO
    """

    serializer_class = ProcedureSerializer
    pagination_class = ProcedurePagination
    permission_classes = [IsAuthenticated, IsPatientAdminOrClinician]

    def get_queryset(self):
        """
        Scoping:
        - patient_admin: all procedures
        - clinician: only procedures where they are the clinician
        - others: no access (handled by permission)
        """
        user = self.request.user
        qs = (
            Procedure.objects.select_related("patient", "clinician", "procedure_type")
            .all()
        )

        if hasattr(user, "clinician_profile"):
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
        is_admin = user.groups.filter(name="patient_admin").exists()
        is_clinician = hasattr(user, "clinician_profile")

        patient = serializer.validated_data["patient"]
        clinician = serializer.validated_data["clinician"]

        if is_clinician and not is_admin:
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


# class ProcedureScheduledPatientsView(GenericAPIView):
#     """
#     GET /api/v1/procedures/scheduled-patients/?procedure_type_id=...

#     - patient_admin: sees all matching procedures
#     - clinician: sees only their own procedures (clinician_id filter ignored)
#     """

#     permission_classes = [IsAuthenticated, IsPatientAdminOrClinician]
#     filter_backends = [DjangoFilterBackend]
#     filterset_class = ProcedureScheduledPatientsFilter

#     def _parse_and_validate_procedure_type(self, request) -> ProcedureType:
#         raw = request.query_params.get("procedure_type_id")
#         if raw is None:
#             # 400 with field error
#             raise ValidationError({"procedure_type_id": ["This field is required."]})

#         try:
#             type_id = int(raw)
#         except (TypeError, ValueError):
#             raise ValidationError({"procedure_type_id": ["Must be an integer."]})

#         try:
#             return ProcedureType.objects.get(pk=type_id)
#         except ProcedureType.DoesNotExist:
#             # 404 if type does not exist
#             raise NotFound("Procedure type not found.")

#     def _validate_date_range(self, request) -> None:
#         """
#         Cross-field check: date_from <= date_to (when both present).

#         django-filter already validates *formats* (via DateFilter),
#         here we only enforce ordering.
#         """
#         date_from = request.query_params.get("date_from")
#         date_to = request.query_params.get("date_to")
#         if not date_from or not date_to:
#             return

#         # Let django-filter / DRF handle format parsing; we only compare strings
#         # parsed as dates. If format is invalid, filter backend will already
#         # produce a 400 before we get here.
#         try:
#             from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
#             to_date = datetime.strptime(date_to, "%Y-%m-%d").date()
#         except ValueError:
#             # If format is bad, let django-filter's DateFilter complain instead.
#             return

#         if from_date > to_date:
#             # non_field_errors in response (as per your tests)
#             raise ValidationError("date_from must be less than or equal to date_to.")

#     def get_base_queryset(self, procedure_type: ProcedureType):
#         """
#         Base queryset before django-filter + role scoping.
#         """
#         user = self.request.user
#         is_admin = user.groups.filter(name="patient_admin").exists()
#         is_clinician = hasattr(user, "clinician_profile")

#         qs = (
#             Procedure.objects.select_related("patient", "clinician")
#             .filter(
#                 procedure_type=procedure_type,
#                 status__in=["PLANNED", "SCHEDULED"],
#                 patient__deleted_at__isnull=True,
#                 clinician__deleted_at__isnull=True,
#             )
#         )

#         if is_clinician and not is_admin:
#             qs = qs.filter(clinician=user.clinician_profile)

#         return qs.order_by("scheduled_at", "id")

#     def get(self, request, *args, **kwargs):
#         # 1. Validate required / special params
#         procedure_type = self._parse_and_validate_procedure_type(request)
#         self._validate_date_range(request)

#         # 2. Base queryset with procedure_type + status + soft-delete + role scoping
#         base_qs = self.get_base_queryset(procedure_type)

#         # 3. Apply django-filter (date_from, date_to, department_id, clinician_id)
#         qs = self.filter_queryset(base_qs)

#         # 4. Pagination + building response payload (manual for speed)
#         page = self.paginate_queryset(qs)
#         results = [
#             {
#                 "procedure": {
#                     "id": proc.id,
#                     "status": proc.status,
#                     "scheduled_at": proc.scheduled_at,
#                     "duration_minutes": proc.duration_minutes,
#                 },
#                 "patient": {
#                     "id": proc.patient.id,
#                     "name": proc.patient.name,
#                     "gender": proc.patient.gender,
#                 },
#                 "clinician": {
#                     "id": proc.clinician.id,
#                     "name": proc.clinician.name,
#                 },
#             }
#             for proc in page
#         ]

#         return self.get_paginated_response(results)


class ProcedureScheduledPatientsView(ListAPIView):
    permission_classes = [IsAuthenticated, IsPatientAdminOrClinician]
    serializer_class = ProcedureScheduledPatientSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProcedureScheduledPatientsFilter
    pagination_class = ProcedurePagination

    def _parse_and_validate_procedure_type(self, request) -> ProcedureType:
        """
        Validate and parse the required procedure_type_id query parameter.
        
        Raises:
            ValidationError: if missing or non-integer.
            NotFound: if procedure type does not exist.
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
                {"non_field_errors": ["date_from must be less than or equal to date_to."]}
            )

    def get_queryset(self):
        # Validation is now done in list() to properly handle exceptions
        # This is called after validation passes, so we can assume
        # procedure_type and date_range are valid
        procedure_type = self.request._validated_procedure_type
        
        user = self.request.user
        is_admin = user.groups.filter(name="patient_admin").exists()
        is_clinician = hasattr(user, "clinician_profile")

        qs = (
            Procedure.objects.select_related("patient", "clinician")
            .filter(
                procedure_type=procedure_type,
                status__in=["PLANNED", "SCHEDULED"],
                patient__deleted_at__isnull=True,
                clinician__deleted_at__isnull=True,
            )
        )

        if is_clinician and not is_admin:
            qs = qs.filter(clinician=user.clinician_profile)

        return qs.order_by("scheduled_at", "id")
    
    def filter_queryset(self, queryset):
        """
        Override to ignore clinician_id filter for clinicians.
        Clinicians should only see their own procedures, so don't let them
        use clinician_id to try to see other clinicians' procedures.
        """
        user = self.request.user
        is_clinician = hasattr(user, "clinician_profile")
        is_admin = user.groups.filter(name="patient_admin").exists()
        
        # For clinicians, bypass clinician_id filter by applying other filters only
        if is_clinician and not is_admin:
            # Get all filter parameters except clinician_id
            params_dict = self.request.query_params.dict()
            params_dict.pop("clinician_id", None)
            
            # Create a new QueryDict from the filtered params
            from django.http import QueryDict
            filtered_params = QueryDict(mutable=True)
            filtered_params.update(params_dict)
            
            # Apply filters manually without clinician_id
            filterset = self.filterset_class(
                filtered_params,
                queryset=queryset,
                request=self.request,
            )
            return filterset.qs
        
        return super().filter_queryset(queryset)
    
    def list(self, request, *args, **kwargs):
        # Perform validation that should return 400/404 errors
        try:
            procedure_type = self._parse_and_validate_procedure_type(request)
            self._validate_date_range(request)
            
            # Store validated procedure_type on request for use in get_queryset
            request._validated_procedure_type = procedure_type
        except (ValidationError, NotFound) as e:
            # Re-raise to let DRF's exception handler process it
            raise
        
        # Call parent list() which will use get_queryset()
        return super().list(request, *args, **kwargs)