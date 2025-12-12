import datetime

from rest_framework import serializers

from apps.clinical.models import Patient, Clinician, Department


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = [
            "id",
            "name",
            "gender",
            "email",
            "date_of_birth",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_date_of_birth(self, value):
        today = datetime.date.today()
        if value > today:
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        return value


class ClinicianSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Clinician
        fields = ("id", "name")


class DepartmentSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ("id", "name")


class ClinicianPatientCountSerializer(serializers.ModelSerializer):
    patient_count = serializers.IntegerField()

    class Meta:
        model = Clinician
        fields = ("id", "name", "patient_count")

"""
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Dr. Smith",
      "patient_count": 2
    },
    {
      "id": 2,
      "name": "Dr. Jones",
      "patient_count": 1
    }
  ]
}
"""