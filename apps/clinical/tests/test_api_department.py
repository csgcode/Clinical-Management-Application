import datetime
from datetime import timedelta

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.clinical.models import (
    Department,
    Clinician,
    Patient,
    PatientClinician,
)


@pytest.mark.django_db
def test_unauthenticated_user_gets_401(
    api_client,
    department_a,
    department_counts_url,
):
    url = department_counts_url(department_a.id)
    response = api_client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_regular_user_gets_403(
    api_client,
    regular_user,
    department_a,
    department_counts_url,
):
    api_client.force_authenticate(user=regular_user)
    url = department_counts_url(department_a.id)
    response = api_client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_clinician_in_other_department_gets_403(
    api_client,
    clinician_user_other_dept,
    clinician_b1,
    department_a,
    department_counts_url,
):
    api_client.force_authenticate(user=clinician_user_other_dept)
    url = department_counts_url(department_a.id)
    response = api_client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN


# -------------------------------------------------------------------
# Patient admin behaviour
# -------------------------------------------------------------------
@pytest.mark.django_db
def test_patient_admin_sees_all_clinicians_with_counts(
    api_client,
    patient_admin_user,
    department_a,
    clinician_a1,
    clinician_a2,
    clinician_a3,
    patient_1,
    patient_2,
    patient_3,
    department_counts_url,
):
    api_client.force_authenticate(user=patient_admin_user)

    now = timezone.now()
    PatientClinician.objects.create(
        patient=patient_1,
        clinician=clinician_a1,
        is_primary=True,
        relationship_start=now,
    )
    PatientClinician.objects.create(
        patient=patient_2,
        clinician=clinician_a1,
        is_primary=False,
        relationship_start=now,
    )
    PatientClinician.objects.create(
        patient=patient_3,
        clinician=clinician_a2,
        is_primary=True,
        relationship_start=now,
    )

    url = department_counts_url(department_a.id)
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    data = response.data

    assert data["department"]["id"] == department_a.id
    assert data["department"]["name"] == department_a.name

    returned = {
        item["clinician"]["id"]: item["patient_count"] for item in data["results"]
    }

    assert data["count"] == 3
    assert clinician_a1.id in returned
    assert clinician_a2.id in returned
    assert clinician_a3.id in returned

    assert returned[clinician_a1.id] == 2
    assert returned[clinician_a2.id] == 1
    assert returned[clinician_a3.id] == 0


@pytest.mark.django_db
def test_patient_admin_pagination(
    api_client,
    patient_admin_user,
    department_a,
    patient_1,
    department_counts_url,
):
    clinicians = []
    for i in range(5):
        c = Clinician.objects.create(
            user=User.objects.create_user(
                email=f"clin_{i}@example.com",
                password="password123",
            ),
            department=department_a,
            name=f"Clin {i}",
        )
        clinicians.append(c)

    PatientClinician.objects.create(
        patient=patient_1,
        clinician=clinicians[0],
        is_primary=True,
        relationship_start=timezone.now(),
    )

    api_client.force_authenticate(user=patient_admin_user)
    url = department_counts_url(department_a.id)

    response = api_client.get(url, {"limit": 2, "offset": 0})
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 5
    assert len(response.data["results"]) == 2

    response2 = api_client.get(url, {"limit": 2, "offset": 2})
    assert response2.status_code == status.HTTP_200_OK
    assert response2.data["count"] == 5
    assert len(response2.data["results"]) == 2 or len(response2.data["results"]) == 1


@pytest.mark.django_db
def test_patient_admin_filter_by_clinician_id(
    api_client,
    patient_admin_user,
    department_a,
    clinician_a1,
    clinician_a2,
    patient_1,
    patient_2,
    department_counts_url,
):
    api_client.force_authenticate(user=patient_admin_user)

    now = timezone.now()
    PatientClinician.objects.create(
        patient=patient_1,
        clinician=clinician_a1,
        is_primary=True,
        relationship_start=now,
    )
    PatientClinician.objects.create(
        patient=patient_2,
        clinician=clinician_a1,
        is_primary=False,
        relationship_start=now,
    )

    url = department_counts_url(department_a.id)
    response = api_client.get(url, {"clinician_id": clinician_a1.id})

    assert response.status_code == status.HTTP_200_OK
    data = response.data
    assert data["count"] == 1
    assert len(data["results"]) == 1
    item = data["results"][0]
    assert item["clinician"]["id"] == clinician_a1.id
    assert item["patient_count"] == 2


@pytest.mark.django_db
def test_patient_admin_filter_by_clinician_not_in_department_returns_empty(
    api_client,
    patient_admin_user,
    department_a,
    department_b,
    clinician_b1,
    department_counts_url,
):
    api_client.force_authenticate(user=patient_admin_user)

    url = department_counts_url(department_a.id)
    response = api_client.get(url, {"clinician_id": clinician_b1.id})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 0
    assert response.data["results"] == []


@pytest.mark.django_db
def test_patient_admin_invalid_clinician_id_type_returns_400(
    api_client,
    patient_admin_user,
    department_a,
    department_counts_url,
):
    api_client.force_authenticate(user=patient_admin_user)

    url = department_counts_url(department_a.id)
    response = api_client.get(url, {"clinician_id": "abc"})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "clinician_id" in response.data


# -------------------------------------------------------------------
# Soft delete / relationship semantics
# -------------------------------------------------------------------
@pytest.mark.django_db
def test_soft_deleted_clinician_excluded(
    api_client,
    patient_admin_user,
    department_a,
    patient_1,
    department_counts_url,
):
    api_client.force_authenticate(user=patient_admin_user)

    active_clinician = Clinician.objects.create(
        user=User.objects.create_user(
            email="active@example.com", password="password123"
        ),
        department=department_a,
        name="Active Clinician",
    )
    deleted_clinician = Clinician.objects.create(
        user=User.objects.create_user(
            email="deleted@example.com", password="password123"
        ),
        department=department_a,
        name="Deleted Clinician",
    )

    now = timezone.now()
    PatientClinician.objects.create(
        patient=patient_1,
        clinician=active_clinician,
        is_primary=True,
        relationship_start=now,
    )
    PatientClinician.objects.create(
        patient=patient_1,
        clinician=deleted_clinician,
        is_primary=False,
        relationship_start=now,
    )

    deleted_clinician.delete()

    url = department_counts_url(department_a.id)
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    returned = {
        item["clinician"]["id"]: item["patient_count"]
        for item in response.data["results"]
    }

    assert active_clinician.id in returned
    assert returned[active_clinician.id] == 1
    assert deleted_clinician.id not in returned


@pytest.mark.django_db
def test_soft_deleted_patient_and_ended_relationship_are_not_counted(
    api_client,
    patient_admin_user,
    department_a,
    clinician_a1,
    patient_1,
    patient_2,
    department_counts_url,
):
    api_client.force_authenticate(user=patient_admin_user)

    now = timezone.now()

    PatientClinician.objects.create(
        patient=patient_1,
        clinician=clinician_a1,
        is_primary=True,
        relationship_start=now,
    )

    PatientClinician.objects.create(
        patient=patient_2,
        clinician=clinician_a1,
        is_primary=False,
        relationship_start=now - datetime.timedelta(days=10),
        relationship_end=now - datetime.timedelta(days=1),
    )

    patient_2.delete()

    url = department_counts_url(department_a.id)
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    returned = {
        item["clinician"]["id"]: item["patient_count"]
        for item in response.data["results"]
    }

    assert returned[clinician_a1.id] == 1


@pytest.mark.django_db
def test_duplicate_links_for_same_patient_are_counted_distinct_once(
    api_client,
    patient_admin_user,
    department_a,
    clinician_a1,
    patient_1,
    department_counts_url,
):
    api_client.force_authenticate(user=patient_admin_user)

    now = timezone.now()
    PatientClinician.objects.create(
        patient=patient_1,
        clinician=clinician_a1,
        is_primary=True,
        relationship_start=now - timedelta(days=3),
    )
    PatientClinician.objects.create(
        patient=patient_1,
        clinician=clinician_a1,
        is_primary=False,
        relationship_start=now,
    )

    url = department_counts_url(department_a.id)
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    returned = {
        item["clinician"]["id"]: item["patient_count"]
        for item in response.data["results"]
    }

    assert returned[clinician_a1.id] == 1


@pytest.mark.django_db
def test_nonexistent_department_returns_404(
    api_client,
    patient_admin_user,
    department_counts_url,
):
    api_client.force_authenticate(user=patient_admin_user)

    url = department_counts_url(999999)
    response = api_client.get(url)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_department_with_no_clinicians_returns_empty_list(
    api_client,
    patient_admin_user,
    department_counts_url,
):
    api_client.force_authenticate(user=patient_admin_user)

    dept = Department.objects.create(name="Empty Dept")
    url = department_counts_url(dept.id)

    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["department"]["id"] == dept.id
    assert response.data["count"] == 0
    assert response.data["results"] == []


# -------------------------------------------------------------------
# Clinician self-view behaviour
# -------------------------------------------------------------------
@pytest.mark.django_db
def test_clinician_can_view_own_patient_count_in_own_department(
    api_client,
    clinician_user_in_dept,
    clinician_a1,
    department_a,
    patient_1,
    patient_2,
    department_counts_url,
):
    api_client.force_authenticate(user=clinician_user_in_dept)

    now = timezone.now()
    PatientClinician.objects.create(
        patient=patient_1,
        clinician=clinician_a1,
        is_primary=True,
        relationship_start=now,
    )
    PatientClinician.objects.create(
        patient=patient_2,
        clinician=clinician_a1,
        is_primary=False,
        relationship_start=now,
    )

    url = department_counts_url(department_a.id)
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    data = response.data
    assert data["count"] == 1
    assert len(data["results"]) == 1

    item = data["results"][0]
    assert item["clinician"]["id"] == clinician_a1.id
    assert item["patient_count"] == 2


@pytest.mark.django_db
def test_clinician_with_no_patients_sees_zero_count(
    api_client,
    clinician_user_in_dept,
    clinician_a1,
    department_a,
    department_counts_url,
):
    api_client.force_authenticate(user=clinician_user_in_dept)

    url = department_counts_url(department_a.id)
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    data = response.data
    assert data["count"] == 1
    assert len(data["results"]) == 1
    item = data["results"][0]
    assert item["clinician"]["id"] == clinician_a1.id
    assert item["patient_count"] == 0


@pytest.mark.django_db
def test_clinician_cannot_use_clinician_id_filter_to_see_others(
    api_client,
    clinician_user_in_dept,
    clinician_a1,
    clinician_a2,
    department_a,
    patient_1,
    department_counts_url,
):
    api_client.force_authenticate(user=clinician_user_in_dept)

    PatientClinician.objects.create(
        patient=patient_1,
        clinician=clinician_a1,
        is_primary=True,
        relationship_start=timezone.now(),
    )

    url = department_counts_url(department_a.id)
    response = api_client.get(url, {"clinician_id": clinician_a2.id})

    assert response.status_code == status.HTTP_200_OK
    data = response.data
    assert data["count"] == 1
    assert len(data["results"]) == 1
    item = data["results"][0]
    assert item["clinician"]["id"] == clinician_a1.id
    assert item["patient_count"] == 1
