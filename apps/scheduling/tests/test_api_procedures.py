
import pytest
from rest_framework import status

from apps.scheduling.models import Procedure


@pytest.mark.django_db
def test_unauthenticated_cannot_create_procedure(api_client, procedure_list_url):
    payload = {
        "patient_id": 1,
        "procedure_type_id": 1,
        "clinician_id": 1,
        "scheduled_at": "2100-01-01T10:00:00Z",
        "status": "PLANNED",
    }
    response = api_client.post(procedure_list_url, payload, format="json")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_regular_user_cannot_create_procedure(
    api_client,
    regular_user,
    procedure_list_url,
    patient,
    active_procedure_type,
    clinician_profile,
):
    api_client.force_authenticate(user=regular_user)
    payload = {
        "patient_id": patient.id,
        "procedure_type_id": active_procedure_type.id,
        "clinician_id": clinician_profile.id,
        "scheduled_at": "2100-01-01T10:00:00Z",
        "status": "PLANNED",
    }
    response = api_client.post(procedure_list_url, payload, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_patient_admin_can_create_procedure_and_defaults_duration(
    api_client,
    patient_admin_user,
    procedure_list_url,
    patient,
    active_procedure_type,
    clinician_profile,
):
    api_client.force_authenticate(user=patient_admin_user)

    payload = {
        "patient_id": patient.id,
        "procedure_type_id": active_procedure_type.id,
        "clinician_id": clinician_profile.id,
        "scheduled_at": "2100-01-01T10:00:00Z",
        "status": "PLANNED",
    }

    response = api_client.post(procedure_list_url, payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED

    data = response.data
    assert "id" in data

    assert data["procedure_type"]["id"] == active_procedure_type.id
    assert data["procedure_type"]["name"] == active_procedure_type.name
    assert data["patient"]["id"] == patient.id
    assert data["patient"]["name"] == patient.name
    assert data["clinician"]["id"] == clinician_profile.id
    assert data["clinician"]["name"] == clinician_profile.name

    assert data["duration_minutes"] == active_procedure_type.default_duration_minutes

    proc = Procedure.objects.get(id=data["id"])
    assert proc.duration_minutes == active_procedure_type.default_duration_minutes
    assert proc.status == "PLANNED"


@pytest.mark.django_db
def test_patient_admin_cannot_schedule_in_past(
    api_client,
    patient_admin_user,
    procedure_list_url,
    patient,
    active_procedure_type,
    clinician_profile,
):
    api_client.force_authenticate(user=patient_admin_user)

    payload = {
        "patient_id": patient.id,
        "procedure_type_id": active_procedure_type.id,
        "clinician_id": clinician_profile.id,
        "scheduled_at": "2000-01-01T10:00:00Z",
        "status": "PLANNED",
    }

    response = api_client.post(procedure_list_url, payload, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "scheduled_at" in response.data


@pytest.mark.django_db
def test_patient_admin_cannot_use_inactive_procedure_type(
    api_client,
    patient_admin_user,
    procedure_list_url,
    patient,
    inactive_procedure_type,
    clinician_profile,
):
    api_client.force_authenticate(user=patient_admin_user)

    payload = {
        "patient_id": patient.id,
        "procedure_type_id": inactive_procedure_type.id,
        "clinician_id": clinician_profile.id,
        "scheduled_at": "2100-01-01T10:00:00Z",
        "status": "PLANNED",
    }

    response = api_client.post(procedure_list_url, payload, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "procedure_type_id" in response.data


@pytest.mark.django_db
def test_patient_admin_cannot_assign_to_soft_deleted_patient_or_clinician(
    api_client,
    patient_admin_user,
    procedure_list_url,
    soft_deleted_patient,
    active_procedure_type,
    soft_deleted_clinician,
):
    api_client.force_authenticate(user=patient_admin_user)

    payload = {
        "patient_id": soft_deleted_patient.id,
        "procedure_type_id": active_procedure_type.id,
        "clinician_id": soft_deleted_clinician.id,
        "scheduled_at": "2100-01-01T10:00:00Z",
        "status": "PLANNED",
    }

    response = api_client.post(procedure_list_url, payload, format="json")
    # TODO
    assert response.status_code in (
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_404_NOT_FOUND,
    )


@pytest.mark.django_db
def test_clinician_can_create_procedure_for_linked_patient_with_self_as_clinician(
    api_client,
    clinician_user,
    clinician_profile,
    linked_patient,
    active_procedure_type,
    procedure_list_url,
):
    api_client.force_authenticate(user=clinician_user)

    payload = {
        "patient_id": linked_patient.id,
        "procedure_type_id": active_procedure_type.id,
        "clinician_id": clinician_profile.id,
        "scheduled_at": "2100-01-01T10:00:00Z",
        "status": "PLANNED",
        "duration_minutes": 45,
    }

    response = api_client.post(procedure_list_url, payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED

    data = response.data
    assert data["patient"]["id"] == linked_patient.id
    assert data["clinician"]["id"] == clinician_profile.id
    assert data["status"] == "PLANNED"
    assert data["duration_minutes"] == 45


@pytest.mark.django_db
def test_clinician_cannot_create_procedure_for_unlinked_patient(
    api_client,
    clinician_user,
    clinician_profile,
    another_patient,
    active_procedure_type,
    procedure_list_url,
):
    api_client.force_authenticate(user=clinician_user)

    payload = {
        "patient_id": another_patient.id,
        "procedure_type_id": active_procedure_type.id,
        "clinician_id": clinician_profile.id,
        "scheduled_at": "2100-01-01T10:00:00Z",
        "status": "PLANNED",
    }

    response = api_client.post(procedure_list_url, payload, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "patient_id" in response.data


@pytest.mark.django_db
def test_clinician_cannot_create_procedure_with_other_clinician_id(
    api_client,
    clinician_user,
    clinician_profile,
    other_clinician_profile,
    linked_patient,
    active_procedure_type,
    procedure_list_url,
):
    api_client.force_authenticate(user=clinician_profile.user)

    payload = {
        "patient_id": linked_patient.id,
        "procedure_type_id": active_procedure_type.id,
        "clinician_id": other_clinician_profile.id,
        "scheduled_at": "2100-01-01T10:00:00Z",
        "status": "PLANNED",
    }

    response = api_client.post(procedure_list_url, payload, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "clinician_id" in response.data
