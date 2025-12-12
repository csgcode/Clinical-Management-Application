from rest_framework.exceptions import ValidationError, NotFound
import django_filters

from apps.scheduling.models import Procedure
from apps.catalog.models import ProcedureType


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

    def filter_queryset(self, queryset):
        """
        Override to validate:
        - procedure_type is required and must exist
        - date_from must be <= date_to when both present
        """
        procedure_type = self.form.cleaned_data.get("procedure_type")
        if procedure_type is None:
            raise ValidationError({"procedure_type": ["This field is required."]})

        if not ProcedureType.objects.filter(pk=procedure_type.pk).exists():
            raise NotFound("Procedure type not found.")

        date_from = self.form.cleaned_data.get("date_from")
        date_to = self.form.cleaned_data.get("date_to")

        if date_from and date_to and date_from > date_to:
            raise ValidationError(
                {"non_field_errors": ["date_from must be less than or equal to date_to."]}
            )

        return super().filter_queryset(queryset)

    class Meta:
        model = Procedure
        fields = ["procedure_type", "date_from", "date_to", "department_id", "clinician"]
