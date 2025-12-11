import datetime

import pytest
from django.contrib.auth.models import Group, Permission
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User
from apps.clinical.models import Patient, PatientClinician
from apps.clinical.tests.conftest import *


@pytest.mark.django_db
def test_unauthenticated_user_get_list(api_client):
    url = reverse("clinical:patient-list")
    response = api_client.get(url)
    print("asdasd:dasdasd", response.data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_unauthenticated_user_post(api_client):
    url = reverse("clinical:patient-list")
    payload = {
        "name": "Jane Doe",
        "gender": "FEMALE",
        "email": "jane@example.com",
        "date_of_birth": "1990-01-01",
    }
    response = api_client.post(url, payload, format="json")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_user_without_group_cannot_access(api_client, db):
    user = User.objects.create_user(email="regular@example.com", password="password123")
    api_client.force_authenticate(user=user)

    list_url = reverse("clinical:patient-list")
    response = api_client.get(list_url)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    response = api_client.post(list_url, {}, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_patient_admin_can_access_all_crud(
    api_client,
    patient_admin_user,
    active_patient,
):
    api_client.force_authenticate(user=patient_admin_user)

    list_url = reverse("clinical:patient-list")

    # list
    response = api_client.get(list_url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] >= 1

    # create
    payload = {
        "name": "New Patient",
        "gender": "FEMALE",
        "email": "new@example.com",
        "date_of_birth": "1999-09-09",
    }
    response = api_client.post(list_url, payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    new_id = response.data["id"]

    # retrieve
    detail_url = reverse("clinical:patient-detail", args=[active_patient.id])
    response = api_client.get(detail_url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == active_patient.id

    # update
    detail_url_new = reverse("clinical:patient-detail", args=[new_id])
    response = api_client.patch(
        detail_url_new,
        {"name": "Updated Name"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["name"] == "Updated Name"

    # delete (soft)
    response = api_client.delete(detail_url_new)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    # ensure soft-deleted does not come back in list
    response = api_client.get(list_url)
    ids = [p["id"] for p in response.data["results"]]
    assert new_id not in ids


@pytest.mark.django_db
def test_clinician_cannot_create_update_delete(
    api_client,
    clinician_profile,
    active_patient,
):
    api_client.force_authenticate(user=clinician_profile.user)

    list_url = reverse("clinical:patient-list")
    detail_url = reverse("clinical:patient-detail", args=[active_patient.id])

    # create
    response = api_client.post(
        list_url,
        {
            "name": "Foo",
            "gender": "MALE",
            "email": "foo@example.com",
            "date_of_birth": "1990-01-01",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # update
    response = api_client.patch(
        detail_url,
        {"name": "Hacked"},
        format="json",
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # delete
    response = api_client.delete(detail_url)
    assert response.status_code == status.HTTP_403_FORBIDDEN


# -------------------------------------------------------------------
# Clinician scoping tests
# -------------------------------------------------------------------


@pytest.mark.django_db
def test_patient_admin_sees_all_non_deleted_patients_in_list(
    api_client,
    patient_admin_user,
    active_patient,
    another_patient,
    soft_deleted_patient,
):
    api_client.force_authenticate(user=patient_admin_user)

    url = reverse("clinical:patient-list")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK

    returned_ids = {p["id"] for p in response.data["results"]}
    assert active_patient.id in returned_ids
    assert another_patient.id in returned_ids
    assert soft_deleted_patient.id not in returned_ids  # soft-deleted excluded


@pytest.mark.django_db
def test_clinician_list_only_returns_linked_patients(
    api_client,
    clinician_profile,
    linked_patient,
    unlinked_patient,
):
    api_client.force_authenticate(user=clinician_profile.user)

    url = reverse("clinical:patient-list")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK

    returned_ids = {p["id"] for p in response.data["results"]}
    assert linked_patient.id in returned_ids
    assert unlinked_patient.id not in returned_ids


@pytest.mark.django_db
def test_clinician_can_retrieve_linked_patient(
    api_client,
    clinician_profile,
    linked_patient,
):
    api_client.force_authenticate(user=clinician_profile.user)

    url = reverse("clinical:patient-detail", args=[linked_patient.id])
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == linked_patient.id


@pytest.mark.django_db
def test_clinician_cannot_retrieve_unlinked_patient(
    api_client,
    clinician_profile,
    unlinked_patient,
):
    api_client.force_authenticate(user=clinician_profile.user)

    url = reverse("clinical:patient-detail", args=[unlinked_patient.id])
    response = api_client.get(url)
    # Should be 404 (not 403) to avoid leaking existence
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_soft_deleted_patient_returns_404_for_admin_and_clinician(
    api_client,
    patient_admin_user,
    clinician_profile,
    soft_deleted_patient,
):
    detail_url = reverse("clinical:patient-detail", args=[soft_deleted_patient.id])

    # admin
    api_client.force_authenticate(user=patient_admin_user)
    response = api_client.get(detail_url)
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # clinician
    api_client.force_authenticate(user=clinician_profile.user)
    response = api_client.get(detail_url)
    assert response.status_code == status.HTTP_404_NOT_FOUND


# -------------------------------------------------------------------
# Search behaviour
# -------------------------------------------------------------------


@pytest.mark.django_db
def test_patient_admin_search_by_name_and_email(
    api_client,
    patient_admin_user,
    db,
):
    p1 = Patient.objects.create(
        name="Jane Doe",
        gender=Patient.Gender.FEMALE,
        email="jane@example.com",
        date_of_birth=datetime.date(1990, 1, 1),
    )
    p2 = Patient.objects.create(
        name="Janet Lee",
        gender=Patient.Gender.FEMALE,
        email="janet@example.com",
        date_of_birth=datetime.date(1991, 2, 2),
    )
    p3 = Patient.objects.create(
        name="John Smith",
        gender=Patient.Gender.MALE,
        email="john.smith@example.com",
        date_of_birth=datetime.date(1985, 5, 5),
    )

    api_client.force_authenticate(user=patient_admin_user)

    url = reverse("clinical:patient-list")

    # search name fragment "jan" => Jane + Janet
    response = api_client.get(url, {"search": "jan"})
    assert response.status_code == status.HTTP_200_OK
    returned_ids = {p["id"] for p in response.data["results"]}
    assert p1.id in returned_ids
    assert p2.id in returned_ids
    assert p3.id not in returned_ids

    # search by email fragment
    response = api_client.get(url, {"search": "smith@"})
    assert response.status_code == status.HTTP_200_OK
    returned_ids = {p["id"] for p in response.data["results"]}
    assert p3.id in returned_ids
    assert p1.id not in returned_ids
    assert p2.id not in returned_ids


@pytest.mark.django_db
def test_clinician_search_is_scoped_to_linked_patients(
    api_client,
    clinician_profile,
    other_clinician_profile,
):
    # two patients with similar names but different clinician links
    my_patient = Patient.objects.create(
        name="Scoped Jane",
        gender=Patient.Gender.FEMALE,
        email="scoped.jane@example.com",
        date_of_birth=datetime.date(1990, 1, 1),
    )
    other_patient = Patient.objects.create(
        name="Scoped Jane Other",
        gender=Patient.Gender.FEMALE,
        email="scoped.jane.other@example.com",
        date_of_birth=datetime.date(1991, 1, 1),
    )

    PatientClinician.objects.create(
        patient=my_patient,
        clinician=clinician_profile,
        is_primary=True,
        relationship_start=datetime.datetime.now(datetime.timezone.utc),
    )
    PatientClinician.objects.create(
        patient=other_patient,
        clinician=other_clinician_profile,
        is_primary=True,
        relationship_start=datetime.datetime.now(datetime.timezone.utc),
    )

    api_client.force_authenticate(user=clinician_profile.user)
    url = reverse("clinical:patient-list")

    response = api_client.get(url, {"search": "Scoped Jane"})
    assert response.status_code == status.HTTP_200_OK
    returned_ids = {p["id"] for p in response.data["results"]}

    # clinician should only see their own patient, not the other
    assert my_patient.id in returned_ids
    assert other_patient.id not in returned_ids
