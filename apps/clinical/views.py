from django.db.models import Q
from django.db.models import Count

from rest_framework import viewsets
from rest_framework.generics import GenericAPIView
from rest_framework.pagination import LimitOffsetPagination
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


class DepartmentClinicianPatientCountPagination(LimitOffsetPagination):
    default_limit = 20
    max_limit = 100


class DepartmentClinicianPatientCountView(GenericAPIView):
    """
    GET /api/v1/departments/{department_id}/clinician-patient-counts/

    - patient_admin:
        * sees all clinicians in the department (paginated)
    - clinician in that department:
        * sees only their own row (count = patients linked to them)
    """

    permission_classes = [IsAuthenticated, IsPatientAdminOrClinicianForDepartment]
    pagination_class = DepartmentClinicianPatientCountPagination
    serializer_class = ClinicianPatientCountSerializer  # for type hints only

    def get(self, request, department_id: int, *args, **kwargs):
        # 1. Resolve department or 404
        try:
            department = Department.objects.get(pk=department_id)
        except Department.DoesNotExist:
            from rest_framework.exceptions import NotFound

            raise NotFound("Department not found.")

        user = request.user
        is_admin = user.groups.filter(name="patient_admin").exists()
        is_clinician = hasattr(user, "clinician_profile")

        # 2. Base clinicians queryset for this department (SoftDeleteManager excludes deleted)
        clinicians_qs = Clinician.objects.filter(department=department)

        # 3. Clinician role → restrict to self only
        if is_clinician and not is_admin:
            clinician_profile = user.clinician_profile
            clinicians_qs = clinicians_qs.filter(pk=clinician_profile.pk)

        # 4. Optional filter: clinician_id (for admins only)
        clinician_id_param = request.query_params.get("clinician_id")
        if clinician_id_param is not None:
            if not is_admin:
                # clinicians cannot use this to see others; ignore it (self-only is already enforced)
                pass
            else:
                # validate integer
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

        # 5. Pagination over clinicians in this department
        clinicians_qs = clinicians_qs.order_by("name", "id")
        page = self.paginate_queryset(clinicians_qs)

        # If there are no clinicians at all (count=0), page will be []
        clinicians_on_page = list(page)

        # 6. Aggregate patient counts for clinicians on this page
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

        # 7. Build results payload
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

        # 8. Use paginator to build paginated response, then inject department meta
        paginated = self.get_paginated_response(results)
        # paginated.data is an OrderedDict with count/next/previous/results
        paginated.data["department"] = DepartmentSummarySerializer(department).data

        # Ensure department appears first or last as you prefer; currently appended
        # If you want it first, you can reorder keys, but not necessary for functionality.

        return paginated
