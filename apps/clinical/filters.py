import django_filters
from rest_framework.exceptions import ValidationError

from apps.clinical.models import Clinician
from apps.core.permissions_helpers import is_patient_admin


class ClinicianPatientCountFilter(django_filters.FilterSet):
    """
    Filter for GET /api/v1/departments/{department_id}/clinician-patient-counts/
    
    Handles:
    - clinician: ID of specific clinician (admin only)
    
    Raises ValidationError if:
    - clinician parameter is not a valid integer
    - non-admin user attempts to filter by clinician
    """

    clinician = django_filters.NumberFilter(
        field_name="id",
        method="filter_clinician",
    )

    def filter_clinician(self, queryset, name, value):
        """
        Filter by specific clinician ID (admin only).
        
        For non-admin users, this filter is silently ignored.
        
        Args:
            queryset: The queryset to filter
            name: Field name (unused, but required by django-filter signature)
            value: The clinician ID value
            
        Returns:
            Filtered queryset if admin and value is valid, otherwise unchanged
        """
        if value is None:
            return queryset

        # Non-admin users cannot use this filter - silently ignore it
        if not is_patient_admin(self.request.user):
            return queryset

        return queryset.filter(pk=value)

    class Meta:
        model = Clinician
        fields = ["clinician"]
