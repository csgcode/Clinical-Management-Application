from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel, SoftDeleteModel


class Department(TimeStampedModel):
    """
    Hospital department, e.g. Cardiology, Radiology.
    """

    name = models.CharField(max_length=255, unique=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "-created_at"]

    def __str__(self) -> str:
        return self.name


class Clinician(TimeStampedModel, SoftDeleteModel):
    """
    Profile for clinicians (doctors, nurses, etc.).
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="clinician_profile",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="clinicians",
    )
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ["name", "-created_at"]
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self) -> str:
        return self.name


class Patient(TimeStampedModel, SoftDeleteModel):
    """
    Domain profile for patients.
    """

    class Gender(models.TextChoices):
        MALE = "MALE", "Male"
        FEMALE = "FEMALE", "Female"
        OTHER = "OTHER", "Other"
        UNKNOWN = "UNKNOWN", "Unknown"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patient_profile",
        help_text="Link to user account for patient portal access.",
    )
    name = models.CharField(max_length=255)
    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
        default=Gender.UNKNOWN,
    )
    email = models.EmailField(
        blank=True,
        null=True,
        db_index=True,
        help_text="Contact email for the patient.",
    )
    date_of_birth = models.DateField()

    clinicians = models.ManyToManyField(
        Clinician,
        through="PatientClinician",
        related_name="patients",
        blank=True,
    )

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self) -> str:
        return self.name


class PatientClinician(TimeStampedModel, SoftDeleteModel):
    """
    Association between Patient and Clinician.
    Represents care responsibility with history/metadata.
    """

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="patient_clinician_links",
    )
    clinician = models.ForeignKey(
        Clinician,
        on_delete=models.CASCADE,
        related_name="patient_clinician_links",
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Indicates if this clinician is the primary clinician for the patient.",
    )
    relationship_start = models.DateTimeField()
    relationship_end = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Null means the relationship is still active.",
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Patient Clinician Link"
        verbose_name_plural = "Patient Clinician Links"

        indexes = [
            models.Index(fields=["patient", "clinician"]),
            models.Index(fields=["clinician", "relationship_end"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["patient", "clinician", "relationship_start"],
                name="uniq_patient_clinician_start",
            )
        ]

    def __str__(self) -> str:
        return f"{self.patient} - {self.clinician}"
