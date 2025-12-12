from django.db.models import Q, Count

from rest_framework import viewsets
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from apps.clinical.models import Patient, Clinician, PatientClinician
from apps.clinical.filters import ClinicianPatientCountFilter
from apps.clinical.serializers import (
    ClinicianPatientCountSerializer,
    PatientSerializer,
)
from apps.clinical.permissions import (
    IsPatientAdminOrClinicianReadOnly,
    IsPatientAdminOrClinicianForDepartment,
)
from apps.core.pagination import StandardPagination
from apps.core.permissions_helpers import is_patient_admin


class PatientViewSet(viewsets.ModelViewSet):
    """
    CRUD for patients with:
    - search by name/email (?search=)
    - full access for patient_admin users
    """

    serializer_class = PatientSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticated, IsPatientAdminOrClinicianReadOnly]
    search_fields = ["name", "email"]

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
        
        if user.has_clinician_profile:
            clinician = user.clinician_profile
            qs = qs.filter(
                patient_clinician_links__clinician=clinician,
                patient_clinician_links__relationship_end__isnull=True,
            ).distinct()
       
        return qs
    

class DepartmentClinicianPatientCountListViewSet(ListAPIView):
    """
    GET /api/v1/clinician-patient-counts/?department=1

    Returns a list of clinicians in a department with their patient counts.

    Required query parameters:
    - department: ID of department

    Optional query parameters:
    - clinician: filter by specific clinician (admin only)

    Scoping:
    - patient_admin: sees all clinicians in the department
    - clinician in that department: sees only themselves
    - clinician in other department: gets 403 (via IsPatientAdminOrClinicianForDepartment)
    
    Annotations:
    - patient_count: count of active patients linked to each clinician
    """

    serializer_class = ClinicianPatientCountSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticated, IsPatientAdminOrClinicianForDepartment]
    filterset_class = ClinicianPatientCountFilter
    search_fields = ['name']

    def get_queryset(self):
        """
        Base queryset:
        1. Filter clinicians by department (via FilterSet)
        2. Apply user scoping (clinicians see only themselves)
        3. Annotate with patient counts
        
        Note: Department access permission is checked by IsPatientAdminOrClinicianForDepartment
        """
        user = self.request.user
        is_admin = is_patient_admin(user)
        is_clinician = user.has_clinician_profile

        qs = Clinician.objects.all()

        # Scoping: non-admin clinicians see only themselves
        if is_clinician and not is_admin:
            qs = qs.filter(pk=user.clinician_profile.pk)

        # Annotate with patient counts
        qs = qs.annotate(
            patient_count=Count(
                'patient_clinician_links__patient',
                filter=Q(
                    patient_clinician_links__relationship_end__isnull=True,
                    patient_clinician_links__deleted_at__isnull=True,
                    patient_clinician_links__patient__deleted_at__isnull=True,
                ),
                distinct=True,
            )
        )

        return qs.order_by("name", "id")
