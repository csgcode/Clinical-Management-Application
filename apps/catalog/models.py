from django.db import models

from apps.core.models import TimeStampedModel
from apps.clinical.models import Department


class ProcedureType(TimeStampedModel):
    """
    Master catalogue of available procedures.
    """

    name = models.CharField(max_length=255)
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique code for this procedure type (e.g. internal or billing code).",
    )
    default_duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Optional default duration for this procedure type.",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="procedure_types",
        help_text="Optional department that typically owns this procedure.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Set to False to retire this type from new procedures.",
    )

    class Meta:
        ordering = ["name", "-created_at"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["code"]),
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"
