from django.utils import timezone
from datetime import date
from rest_framework import serializers

from apps.clinical.models import Patient, Clinician, PatientClinician
from apps.scheduling.models import Procedure, ProcedureType


class ProcedureTypeSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcedureType
        fields = ("id", "name")


class PatientSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ("id", "name")


class ClinicianSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Clinician
        fields = ("id", "name")


class ProcedureSerializer(serializers.ModelSerializer):
    patient_id = serializers.PrimaryKeyRelatedField(
        source="patient",
        queryset=Patient.objects.all(),
        write_only=True,
    )
    procedure_type_id = serializers.PrimaryKeyRelatedField(
        source="procedure_type",
        queryset=ProcedureType.objects.filter(is_active=True),
        write_only=True,
    )
    clinician_id = serializers.PrimaryKeyRelatedField(
        source="clinician",
        queryset=Clinician.objects.all(),
        write_only=True,
    )

    patient = PatientSummarySerializer(read_only=True)
    procedure_type = ProcedureTypeSummarySerializer(read_only=True)
    clinician = ClinicianSummarySerializer(read_only=True)

    class Meta:
        model = Procedure
        fields = [
            "id",
            "procedure_type",
            "procedure_type_id",
            "patient",
            "patient_id",
            "clinician",
            "clinician_id",
            "name",
            "scheduled_at",
            "duration_minutes",
            "status",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        """
        Cross-field validation:
        - scheduled_at >= now for PLANNED / SCHEDULED
        - clinicians can only assign procedures to themselves
        - clinicians must be linked to patient via active PatientClinician
        """
        attrs = super().validate(attrs)
        request = self.context.get("request")
        user = getattr(request, "user", None)

        patient = attrs.get("patient")
        clinician = attrs.get("clinician")
        procedure_type = attrs.get("procedure_type")
        scheduled_at = attrs.get("scheduled_at")
        status_value = attrs.get("status")

        errors = {}

        if status_value in ("PLANNED", "SCHEDULED"):
            # TODO set defaults
            if scheduled_at is None:
                errors["scheduled_at"] = [
                    "This field is required for PLANNED or SCHEDULED procedures."
                ]
            else:
                now = timezone.now()
                if scheduled_at < now:
                    errors["scheduled_at"] = [
                        "scheduled_at must be in the future for PLANNED or SCHEDULED procedures."
                    ]

        is_admin = (
            user
            and user.is_authenticated
            and user.groups.filter(name="patient_admin").exists()
        )
        is_clinician_user = (
            user and user.is_authenticated and hasattr(user, "clinician_profile")
        )

        if is_clinician_user and not is_admin:
            # TODO check the duplicate logic
            clinician_profile = user.clinician_profile

            if clinician != clinician_profile:
                errors["clinician_id"] = [
                    "Clinicians can only assign procedures to themselves."
                ]

            if patient and clinician:
                has_link = PatientClinician.objects.filter(
                    patient=patient,
                    clinician=clinician,
                    relationship_end__isnull=True,
                    deleted_at__isnull=True,
                ).exists()
                if not has_link:
                    errors["patient_id"] = [
                        "You do not have access to this patient."
                    ]

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def create(self, validated_data):
        procedure_type: ProcedureType = validated_data.get("procedure_type")
        duration = validated_data.get("duration_minutes")

        # Fill duration_minutes from ProcedureType.default_duration_minutes if missing.
        if (
            duration is None
            and procedure_type
            and procedure_type.default_duration_minutes
        ):
            validated_data["duration_minutes"] = procedure_type.default_duration_minutes

        if not validated_data.get("name") and procedure_type:
            validated_data["name"] = procedure_type.name

        return super().create(validated_data)


class ProcedureScheduledPatientsQuerySerializer(serializers.Serializer):
    """
    Validates query params for:
    GET /api/v1/procedures/scheduled-patients/
    """

    procedure_type_id = serializers.IntegerField(required=True)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    department_id = serializers.IntegerField(required=False)
    clinician_id = serializers.IntegerField(required=False)

    def validate(self, attrs):
        date_from: date | None = attrs.get("date_from")
        date_to: date | None = attrs.get("date_to")

        if date_from and date_to and date_from > date_to:
            raise serializers.ValidationError(
                "date_from must be less than or equal to date_to."
            )
        return attrs


class ProcedureMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Procedure
        fields = ("id", "status", "scheduled_at", "duration_minutes")


class ProcedureScheduledPatientSerializer(serializers.Serializer):
    """
    Serializer for the scheduled-patients endpoint response.
    Returns a grouped structure with procedure, patient, and clinician info.
    """

    class ProcedureMinimalSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        status = serializers.CharField()
        scheduled_at = serializers.DateTimeField()
        duration_minutes = serializers.IntegerField()

    procedure = ProcedureMinimalSerializer()
    patient = PatientSummarySerializer()
    clinician = ClinicianSummarySerializer()

    def to_representation(self, instance):
        """
        Transform a Procedure instance into the grouped response format.
        """
        return {
            "procedure": {
                "id": instance.id,
                "status": instance.status,
                "scheduled_at": instance.scheduled_at,
                "duration_minutes": instance.duration_minutes,
            },
            "patient": {
                "id": instance.patient.id,
                "name": instance.patient.name,
                "gender": instance.patient.gender,
            },
            "clinician": {
                "id": instance.clinician.id,
                "name": instance.clinician.name,
            },
        }
