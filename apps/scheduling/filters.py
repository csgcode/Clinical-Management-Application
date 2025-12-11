# apps/scheduling/api/filters.py
import django_filters

from apps.scheduling.models import Procedure


class ProcedureScheduledPatientsFilter(django_filters.FilterSet):
    """
    Filter for GET /api/v1/procedures/scheduled-patients/
    """

    date_from = django_filters.DateFilter(
        field_name="scheduled_at",
        lookup_expr="date__gte",
    )
    date_to = django_filters.DateFilter(
        field_name="scheduled_at",
        lookup_expr="date__lte",
    )
    department_id = django_filters.NumberFilter(
        field_name="clinician__department_id",
    )
    clinician_id = django_filters.NumberFilter(
        field_name="clinician_id",
    )

    class Meta:
        model = Procedure
        fields = []
