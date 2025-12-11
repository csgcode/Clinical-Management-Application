import datetime

import pytest
from django.contrib.auth.models import Group, Permission
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User
from apps.clinical.models import (
    Patient,
    Clinician,
    PatientClinician,
    Department,
)
from apps.scheduling.models import ProcedureType, Procedure


@pytest.fixture
def api_client():
    return APIClient()



@pytest.fixture
def patient_admin_group(db):
    group, _ = Group.objects.get_or_create(name="patient_admin")
    perms = Permission.objects.filter(
        content_type__app_label="clinical",
        content_type__model="patient",
        codename__in=[
            "view_patient",
        ],
    )
    # patient_admin will also need perms on Procedure in a mature setup,
    # but for API-level tests we mostly rely on our custom permission class.

    # TODO create a permission for clinicians to create new procedures
    group.permissions.set(perms)
    return group


@pytest.fixture
def patient_admin_user(db, patient_admin_group):
    user = User.objects.create_user(
        email="admin@example.com",
        password="password123",
        is_staff=True,
    )
    user.groups.add(patient_admin_group)
    return user


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        email="regular@example.com",
        password="password123",
    )


@pytest.fixture
def clinician_user(db):
    return User.objects.create_user(
        email="doc@example.com",
        password="password123",
    )


@pytest.fixture
def other_clinician_user(db):
    return User.objects.create_user(
        email="otherdoc@example.com",
        password="password123",
    )



@pytest.fixture
def department(db):
    return Department.objects.create(name="Radiology")


@pytest.fixture
def clinician_profile(db, clinician_user, department):
    return Clinician.objects.create(
        user=clinician_user,
        department=department,
        name="Dr. Strange",
    )


@pytest.fixture
def other_clinician_profile(db, other_clinician_user, department):
    return Clinician.objects.create(
        user=other_clinician_user,
        department=department,
        name="Dr. House",
    )


@pytest.fixture
def patient(db):
    return Patient.objects.create(
        name="Jane Doe",
        gender=Patient.Gender.FEMALE,
        email="jane@example.com",
        date_of_birth=datetime.date(1990, 1, 1),
    )


@pytest.fixture
def linked_patient(db, patient, clinician_profile):
    # Make clinician_profile the active clinician for patient
    PatientClinician.objects.create(
        patient=patient,
        clinician=clinician_profile,
        is_primary=True,
        relationship_start=timezone.now(),
        relationship_end=None,
    )
    return patient


@pytest.fixture
def another_patient(db):
    return Patient.objects.create(
        name="John Smith",
        gender=Patient.Gender.MALE,
        email="john.smith@example.com",
        date_of_birth=datetime.date(1985, 5, 5),
    )


@pytest.fixture
def soft_deleted_patient(db):
    p = Patient.objects.create(
        name="Deleted Patient",
        gender=Patient.Gender.OTHER,
        email="deleted@example.com",
        date_of_birth=datetime.date(1970, 1, 1),
    )
    p.delete()
    return p


@pytest.fixture
def soft_deleted_clinician(db, department):
    c = Clinician.objects.create(
        user=User.objects.create_user(
            email="deletedclinician@example.com",
            password="password123",
        ),
        department=department,
        name="Dr. Deleted",
    )
    c.delete()
    return c


# -----------------------------
# ProcedureType fixtures
# -----------------------------
@pytest.fixture
def active_procedure_type(db, department):
    return ProcedureType.objects.create(
        name="MRI Brain",
        code="MRI_BRAIN",
        default_duration_minutes=30,
        department=department,
        is_active=True,
    )


@pytest.fixture
def inactive_procedure_type(db, department):
    return ProcedureType.objects.create(
        name="Old Test",
        code="OLD_TEST",
        default_duration_minutes=10,
        department=department,
        is_active=False,
    )



@pytest.fixture
def procedure_list_url():
    return reverse("scheduling:procedure-list")


# -------------------------------------------------------------------
# Auth / permission basics
# -------------------------------------------------------------------
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


# -------------------------------------------------------------------
# Patient admin behaviour
# -------------------------------------------------------------------
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

    # minimal nested output
    assert data["procedure_type"]["id"] == active_procedure_type.id
    assert data["procedure_type"]["name"] == active_procedure_type.name
    assert data["patient"]["id"] == patient.id
    assert data["patient"]["name"] == patient.name
    assert data["clinician"]["id"] == clinician_profile.id
    assert data["clinician"]["name"] == clinician_profile.name

    # default duration filled
    assert data["duration_minutes"] == active_procedure_type.default_duration_minutes

    # ensure DB persisted correctly
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

    # far past date
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
    # Treat as invalid input / not found – 400 with field errors or 404 both acceptable;
    # TODO
    assert response.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND)


# -------------------------------------------------------------------
# Clinician behaviour & scoping
# -------------------------------------------------------------------
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
    assert response.status_code in (
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
    )


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
