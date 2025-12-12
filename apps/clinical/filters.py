import django_filters
from rest_framework.exceptions import ValidationError

from apps.clinical.models import Clinician, Department
from apps.core.permissions_helpers import is_patient_admin


class ClinicianPatientCountFilter(django_filters.FilterSet):
    """
    Filter for GET /api/v1/clinician-patient-counts/?department=1
    
    Required query parameters:
    - department: ID of department (required)
    
    Optional query parameters:
    - clinician: filter by specific clinician (admin only)
    """

    department = django_filters.NumberFilter(
        field_name="department_id",
        method="filter_department",
    )

    clinician = django_filters.NumberFilter(
        field_name="id",
        method="filter_clinician",
    )

    def filter_department(self, queryset, name, value):
        """
        Filter by department ID
        """
        if value is None:
            raise ValidationError(
                {"department": ["This field is required."]}
            )

        if not Department.objects.filter(pk=value).exists():
            raise ValidationError(
                {"department": ["Invalid department ID."]}
            )

        return queryset.filter(department_id=value)

    def filter_clinician(self, queryset, name, value):
        """
        Filter by specific clinician ID (admin only).
        """
        if value is None:
            return queryset

        # Non-admin users cannot use this filter
        if not is_patient_admin(self.request.user):
            return queryset

        return queryset.filter(pk=value)

    class Meta:
        model = Clinician
        fields = ["department", "clinician"]
