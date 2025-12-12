from rest_framework import viewsets
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from apps.scheduling.models import Procedure
from apps.scheduling.serializers import (
    ProcedureScheduledPatientSerializer,
    ProcedureSerializer,
)
from apps.scheduling.permissions import IsPatientAdminOrClinician
from apps.scheduling.filters import ProcedureScheduledPatientsFilter
from apps.core.pagination import StandardPagination
from apps.core.permissions_helpers import is_patient_admin, is_clinician


class ProcedureViewSet(viewsets.ModelViewSet):
    """
    Procedures API

    - POST /api/v1/procedures/       (assign procedure to patient)
    - GET /api/v1/procedures/        (list)
    - GET /api/v1/procedures/{id}/   (detail)
    - PATCH/DELETE
    """

    serializer_class = ProcedureSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticated, IsPatientAdminOrClinician]
    filterset_class = ProcedureScheduledPatientsFilter

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


class ProcedureScheduledPatientsView(ListAPIView):
    """
    GET /api/v1/procedures/scheduled-patients/?procedure_type_id=...

    Lists patients scheduled for a specific procedure type with filtering options.

    - patient_admin: sees all matching procedures
    - clinician: sees only their own procedures (clinician_id filter ignored)
    """

    permission_classes = [IsAuthenticated, IsPatientAdminOrClinician]
    serializer_class = ProcedureScheduledPatientSerializer
    filterset_class = ProcedureScheduledPatientsFilter
    pagination_class = StandardPagination

    def get_queryset(self):
        """
        Get filtered queryset of procedures for the requested procedure type.

        Returns:
            QuerySet of Procedure objects filtered by type, status, and user role.
        """
        user = self.request.user
        admin = is_patient_admin(user)
        clinician = is_clinician(user)

        qs = Procedure.objects.select_related("patient", "clinician").filter(
            status__in=Procedure.ACTIVE_PROCEDURE_STATUSES,
            patient__deleted_at__isnull=True,
            clinician__deleted_at__isnull=True,
        )

        if clinician and not admin:
            qs = qs.filter(clinician=user.clinician_profile)

        return qs.order_by("scheduled_at", "id")

