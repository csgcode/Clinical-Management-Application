from django.utils import timezone
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated

from apps.clinical.models import PatientClinician
from apps.scheduling.models import Procedure
from apps.scheduling.serializers import ProcedureSerializer
from apps.scheduling.permissions import IsPatientAdminOrClinician


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

        if user.groups.filter(name="patient_admin").exists():
            return qs

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
