from django.db.models import Q, Count

from rest_framework import viewsets
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.clinical.models import Patient, Clinician, Department, PatientClinician
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
    - soft delete
    - search by name/email (?search=)
    - scoped access for clinicians (only their patients)
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
    GET /api/v1/departments/{department_id}/clinician-patient-counts/

    Returns a list of clinicians in a department with their patient counts.

    Query parameters:
    - clinician: filter by specific clinician (admin only)
    
    """

    serializer_class = ClinicianPatientCountSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticated, IsPatientAdminOrClinicianForDepartment]
    filterset_class = ClinicianPatientCountFilter
    search_fields = ['name']

    def get_queryset(self):
        department_id = self.kwargs.get('department_id')
        
        try:
            department = Department.objects.get(pk=department_id)
        except Department.DoesNotExist:
            raise NotFound("Department not found.")

        user = self.request.user
        is_admin = is_patient_admin(user)
        is_clinician = user.has_clinician_profile

        qs = Clinician.objects.filter(department=department)

        if is_clinician and not is_admin:
            qs = qs.filter(pk=user.clinician_profile.pk)

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
