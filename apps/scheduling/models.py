from django.db import models

from apps.core.models import TimeStampedModel, SoftDeleteModel
from apps.clinical.models import Patient, Clinician
from apps.catalog.models import ProcedureType


class Procedure(TimeStampedModel, SoftDeleteModel):
    """
    A scheduled or completed procedure for a patient.
    """

    class ProcedureStatus(models.TextChoices):
        PLANNED = "PLANNED", "Planned"
        SCHEDULED = "SCHEDULED", "Scheduled"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        NO_SHOW = "NO_SHOW", "No Show"
        VOID = "VOID", "Void"

    procedure_type = models.ForeignKey(
        ProcedureType,
        on_delete=models.PROTECT,
        related_name="procedures",
    )
    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="procedures",
    )
    clinician = models.ForeignKey(
        Clinician,
        on_delete=models.PROTECT,
        related_name="procedures",
    )
    name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional custom name; if blank, use the procedure type name.",
    )
    scheduled_at = models.DateTimeField(db_index=True)
    duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="If null, Services may fall back to the procedure type duration default.",
    )
    status = models.CharField(
        max_length=20,
        choices=ProcedureStatus.choices,
        default=ProcedureStatus.PLANNED,
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-scheduled_at"]
        indexes = [
            models.Index(fields=["scheduled_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["clinician", "scheduled_at"]),
        ]

    def __str__(self) -> str:
        display_name = self.name or self.procedure_type.name
        return f"{display_name} for {self.patient} at {self.scheduled_at}"
