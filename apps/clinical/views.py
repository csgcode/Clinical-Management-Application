from django.db.models import Q, Count

from rest_framework import viewsets
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated

from apps.clinical.models import Patient, Clinician, Department, PatientClinician
from apps.clinical.serializers import (
    PatientSerializer,
    ClinicianPatientCountSerializer,
    DepartmentSummarySerializer,
)
from apps.clinical.permissions import (
    IsPatientAdminOrClinicianReadOnly,
    IsPatientAdminOrClinicianForDepartment,
)
from apps.core.pagination import StandardPagination
from apps.core.permissions_helpers import is_patient_admin, is_clinician


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
        if is_patient_admin(user):
            base_qs = qs

        elif is_clinician(user):
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


class DepartmentClinicianPatientCountView(GenericAPIView):
    """
    GET /api/v1/departments/{department_id}/clinician-patient-counts/

    - patient_admin:
        * sees all clinicians in the department (paginated)
    - clinician in that department:
        * sees only their own row (count = patients linked to them)
    """

    permission_classes = [IsAuthenticated, IsPatientAdminOrClinicianForDepartment]
    pagination_class = StandardPagination
    serializer_class = ClinicianPatientCountSerializer

    def get(self, request, department_id: int, *args, **kwargs):
        """
        Retrieve clinician patient counts for a specific department.

        Args:
            request: HTTP request object
            department_id: Department ID from URL path
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Paginated response with clinician patient count data
        """
        # 1. Resolve department or 404
        try:
            department = Department.objects.get(pk=department_id)
        except Department.DoesNotExist:
            from rest_framework.exceptions import NotFound

            raise NotFound("Department not found.")

        user = request.user
        admin = is_patient_admin(user)
        clinician = is_clinician(user)

        clinicians_qs = Clinician.objects.filter(department=department)

        if clinician and not admin:
            clinician_profile = user.clinician_profile
            clinicians_qs = clinicians_qs.filter(pk=clinician_profile.pk)

        clinician_id_param = request.query_params.get("clinician_id")
        if clinician_id_param is not None:
            if not admin:
                pass
            else:
                try:
                    clinician_id = int(clinician_id_param)
                except ValueError:
                    from rest_framework.response import Response
                    from rest_framework import status

                    return Response(
                        {"clinician_id": ["Must be an integer."]},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                clinicians_qs = clinicians_qs.filter(pk=clinician_id)

        clinicians_qs = clinicians_qs.order_by("name", "id")
        page = self.paginate_queryset(clinicians_qs)
        clinicians_on_page = list(page)
        if clinicians_on_page:
            counts_qs = (
                PatientClinician.objects.filter(
                    clinician__in=clinicians_on_page,
                    relationship_end__isnull=True,
                    deleted_at__isnull=True,
                    patient__deleted_at__isnull=True,
                )
                .values("clinician_id")
                .annotate(patient_count=Count("patient_id", distinct=True))
            )
            counts_map = {
                row["clinician_id"]: row["patient_count"] for row in counts_qs
            }
        else:
            counts_map = {}

        results = []
        for clinician in clinicians_on_page:
            results.append(
                {
                    "clinician": {
                        "id": clinician.id,
                        "name": clinician.name,
                    },
                    "patient_count": counts_map.get(clinician.id, 0),
                }
            )

        paginated = self.get_paginated_response(results)
        paginated.data["department"] = DepartmentSummarySerializer(department).data

        return paginated
