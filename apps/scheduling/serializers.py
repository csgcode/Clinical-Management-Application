from django.utils import timezone
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
        - clinicians can only assign procedures to themselves (clinician_id == their profile)
        - ProcedureType is already filtered to is_active via queryset
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
        is_clinician = user and user.is_authenticated and hasattr(
            user, "clinician_profile"
        )

        if is_clinician and not is_admin:
            # TODO check the duplciaate logic
            clinician_profile = user.clinician_profile

            # clinicians can only assign themselves as clinician
            if clinician != clinician_profile:
                errors["clinician_id"] = [
                    "Clinicians can only assign procedures to themselves."
                ]

        if errors:
            raise serializers.ValidationError(errors)

        # TODO move to create
        if not attrs.get("name") and procedure_type:
            attrs["name"] = procedure_type.name

        return attrs

    def create(self, validated_data):
        procedure_type: ProcedureType = validated_data.get("procedure_type")
        duration = validated_data.get("duration_minutes")

        # Fill duration_minutes from ProcedureType.default_duration_minutes if missing.
        if duration is None and procedure_type and procedure_type.default_duration_minutes:
            validated_data["duration_minutes"] = procedure_type.default_duration_minutes

        return super().create(validated_data)
