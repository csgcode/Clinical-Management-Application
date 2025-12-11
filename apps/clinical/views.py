from django.db.models import Q
from rest_framework import viewsets
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated

from apps.clinical.models import Patient
from apps.clinical.serializers import PatientSerializer
from apps.clinical.permissions import IsPatientAdminOrClinicianReadOnly


class PatientPagination(LimitOffsetPagination):
    default_limit = 20
    max_limit = 100


class PatientViewSet(viewsets.ModelViewSet):
    """
    CRUD for patients with:
    - soft delete
    - search by name/email (?search=)
    - scoped access for clinicians (only their patients)
    - full access for patient_admin users
    """

    serializer_class = PatientSerializer
    pagination_class = PatientPagination
    permission_classes = [IsAuthenticated, IsPatientAdminOrClinicianReadOnly]

    def get_queryset(self):
        """
        Base queryset:
        - Patient.objects already excludes soft-deleted rows.

        Scoping:
        - patient_admin: all patients
        - clinician: only patients linked via PatientClinician (active links)
        - others: no results
        """
        user = self.request.user
        qs = Patient.objects.all()

        # Change this to permissions?
        if user.groups.filter(name="patient_admin").exists():
            base_qs = qs
        
        elif hasattr(user, "clinician_profile"):
            clinician = user.clinician_profile
            base_qs = qs.filter(
                patient_clinician_links__clinician=clinician,
                patient_clinician_links__relationship_end__isnull=True,
            ).distinct()
        else:
            base_qs = qs.none()

        search = self.request.query_params.get("search")
        if search:
            base_qs = base_qs.filter(
                Q(name__icontains=search) | Q(email__icontains=search)
            )

        return base_qs

