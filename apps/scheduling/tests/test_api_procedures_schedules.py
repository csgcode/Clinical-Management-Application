import datetime

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.clinical.models import Patient, Clinician, Department
from apps.scheduling.models import Procedure, ProcedureType


@pytest.mark.django_db
def test_unauthenticated_gets_401(api_client, scheduled_patients_url, active_type):
    response = api_client.get(
        scheduled_patients_url,
        {"procedure_type": active_type.id},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_regular_user_gets_403(
    api_client,
    regular_user,
    scheduled_patients_url,
    active_type,
):
    api_client.force_authenticate(user=regular_user)
    response = api_client.get(
        scheduled_patients_url,
        {"procedure_type": active_type.id},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


# -------------------------------------------------------------------
# Required params / basic validation
# -------------------------------------------------------------------
@pytest.mark.django_db
def test_missing_procedure_type_returns_400(
    api_client,
    patient_admin_user,
    scheduled_patients_url,
):
    api_client.force_authenticate(user=patient_admin_user)
    response = api_client.get(scheduled_patients_url)
    assert "procedure_type" in response.data


@pytest.mark.django_db
def test_invalid_procedure_type_type_returns_4XX(
    api_client,
    patient_admin_user,
    scheduled_patients_url,
):
    api_client.force_authenticate(user=patient_admin_user)
    response = api_client.get(scheduled_patients_url, {"procedure_type": "abc"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "procedure_type" in response.data


@pytest.mark.django_db
def test_nonexistent_procedure_type_returns_404(
    api_client,
    patient_admin_user,
    scheduled_patients_url,
):
    api_client.force_authenticate(user=patient_admin_user)
    response = api_client.get(scheduled_patients_url, {"procedure_type": 999999})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "procedure_type" in response.data


@pytest.mark.django_db
def test_inactive_procedure_type_returns_empty_list(
    api_client,
    patient_admin_user,
    scheduled_patients_url,
    inactive_type,
):
    api_client.force_authenticate(user=patient_admin_user)
    response = api_client.get(
        scheduled_patients_url,
        {"procedure_type": inactive_type.id},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 0
    assert response.data["results"] == []


@pytest.mark.django_db
def test_admin_lists_scheduled_patients_for_type_default_statuses(
    api_client,
    patient_admin_user,
    scheduled_patients_url,
    active_type,
    other_type,
    clinician_a,
    clinician_b,
    patient_1,
    patient_2,
    patient_3,
):
    """
    Only PLANNED and SCHEDULED for the given type, sorted by scheduled_at asc.
    COMPLETED / CANCELLED and other types are excluded.
    """
    api_client.force_authenticate(user=patient_admin_user)

    now = timezone.now()
    later = now + datetime.timedelta(hours=1)
    much_later = now + datetime.timedelta(hours=2)

    proc1 = Procedure.objects.create(
        procedure_type=active_type,
        patient=patient_1,
        clinician=clinician_a,
        status="SCHEDULED",
        scheduled_at=later,
        duration_minutes=30,
    )
    proc2 = Procedure.objects.create(
        procedure_type=active_type,
        patient=patient_2,
        clinician=clinician_b,
        status="PLANNED",
        scheduled_at=now,
        duration_minutes=45,
    )

    Procedure.objects.create(
        procedure_type=active_type,
        patient=patient_3,
        clinician=clinician_a,
        status="COMPLETED",
        scheduled_at=much_later,
        duration_minutes=10,
    )
    Procedure.objects.create(
        procedure_type=other_type,
        patient=patient_3,
        clinician=clinician_a,
        status="SCHEDULED",
        scheduled_at=much_later,
        duration_minutes=10,
    )

    response = api_client.get(
        scheduled_patients_url,
        {"procedure_type": active_type.id},
    )
    assert response.status_code == status.HTTP_200_OK

    data = response.data
    assert data["count"] == 2
    results = data["results"]
    assert len(results) == 2

    assert results[0]["procedure"]["id"] == proc2.id
    assert results[1]["procedure"]["id"] == proc1.id

    for item in results:
        patient = item["patient"]
        assert set(patient.keys()) == {"id", "name", "gender"}

        clinician = item["clinician"]
        assert set(clinician.keys()) == {"id", "name"}

        procedure = item["procedure"]
        assert "id" in procedure
        assert "status" in procedure
        assert "scheduled_at" in procedure
        assert "duration_minutes" in procedure


@pytest.mark.django_db
def test_admin_filters_by_date_range(
    api_client,
    patient_admin_user,
    scheduled_patients_url,
    active_type,
    clinician_a,
    patient_1,
    patient_2,
    patient_3,
):
    api_client.force_authenticate(user=patient_admin_user)

    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    tomorrow = today + datetime.timedelta(days=1)

    dt_yesterday = datetime.datetime.combine(
        yesterday, datetime.time(10, 0), tzinfo=timezone.UTC
    )
    dt_today = datetime.datetime.combine(
        today, datetime.time(10, 0), tzinfo=timezone.UTC
    )
    dt_tomorrow = datetime.datetime.combine(
        tomorrow, datetime.time(10, 0), tzinfo=timezone.UTC
    )

    p_y = Procedure.objects.create(
        procedure_type=active_type,
        patient=patient_1,
        clinician=clinician_a,
        status="SCHEDULED",
        scheduled_at=dt_yesterday,
        duration_minutes=30,
    )
    p_t = Procedure.objects.create(
        procedure_type=active_type,
        patient=patient_2,
        clinician=clinician_a,
        status="SCHEDULED",
        scheduled_at=dt_today,
        duration_minutes=30,
    )
    p_tm = Procedure.objects.create(
        procedure_type=active_type,
        patient=patient_3,
        clinician=clinician_a,
        status="SCHEDULED",
        scheduled_at=dt_tomorrow,
        duration_minutes=30,
    )

    resp1 = api_client.get(
        scheduled_patients_url,
        {
            "procedure_type": active_type.id,
            "date_from": today.isoformat(),
        },
    )
    assert resp1.status_code == status.HTTP_200_OK
    ids1 = [r["procedure"]["id"] for r in resp1.data["results"]]
    assert p_t.id in ids1
    assert p_tm.id in ids1
    assert p_y.id not in ids1

    resp2 = api_client.get(
        scheduled_patients_url,
        {
            "procedure_type": active_type.id,
            "date_to": today.isoformat(),
        },
    )
    assert resp2.status_code == status.HTTP_200_OK
    ids2 = [r["procedure"]["id"] for r in resp2.data["results"]]
    assert p_y.id in ids2
    assert p_t.id in ids2
    assert p_tm.id not in ids2

    resp3 = api_client.get(
        scheduled_patients_url,
        {
            "procedure_type": active_type.id,
            "date_from": today.isoformat(),
            "date_to": today.isoformat(),
        },
    )
    assert resp3.status_code == status.HTTP_200_OK
    ids3 = [r["procedure"]["id"] for r in resp3.data["results"]]
    assert ids3 == [p_t.id]


@pytest.mark.django_db
def test_invalid_date_format_returns_400(
    api_client,
    patient_admin_user,
    scheduled_patients_url,
    active_type,
):
    api_client.force_authenticate(user=patient_admin_user)

    resp = api_client.get(
        scheduled_patients_url,
        {"procedure_type": active_type.id, "date_from": "2025-13-40"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "date_from" in resp.data


@pytest.mark.django_db
def test_date_from_greater_than_date_to_returns_400(
    api_client,
    patient_admin_user,
    scheduled_patients_url,
    active_type,
):
    api_client.force_authenticate(user=patient_admin_user)

    resp = api_client.get(
        scheduled_patients_url,
        {
            "procedure_type": active_type.id,
            "date_from": "2025-12-31",
            "date_to": "2025-01-01",
        },
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "non_field_errors" in resp.data


@pytest.mark.django_db
def test_admin_filters_by_department(
    api_client,
    patient_admin_user,
    scheduled_patients_url,
    active_type,
    clinician_a,
    clinician_b,
    patient_1,
    patient_2,
):
    """
    department_id filters by clinician.department_id
    """
    api_client.force_authenticate(user=patient_admin_user)

    p_a = Procedure.objects.create(
        procedure_type=active_type,
        patient=patient_1,
        clinician=clinician_a,  # dept A
        status="SCHEDULED",
        scheduled_at=timezone.now(),
        duration_minutes=30,
    )
    p_b = Procedure.objects.create(
        procedure_type=active_type,
        patient=patient_2,
        clinician=clinician_b,  # dept B
        status="SCHEDULED",
        scheduled_at=timezone.now(),
        duration_minutes=30,
    )

    resp_a = api_client.get(
        scheduled_patients_url,
        {
            "procedure_type": active_type.id,
            "department_id": clinician_a.department_id,
        },
    )
    assert resp_a.status_code == status.HTTP_200_OK
    ids_a = [r["procedure"]["id"] for r in resp_a.data["results"]]
    assert p_a.id in ids_a
    assert p_b.id not in ids_a

    resp_b = api_client.get(
        scheduled_patients_url,
        {
            "procedure_type": active_type.id,
            "department_id": clinician_b.department_id,
        },
    )
    assert resp_b.status_code == status.HTTP_200_OK
    ids_b = [r["procedure"]["id"] for r in resp_b.data["results"]]
    assert p_b.id in ids_b
    assert p_a.id not in ids_b


@pytest.mark.django_db
def test_admin_invalid_department_id_type_returns_400(
    api_client,
    patient_admin_user,
    scheduled_patients_url,
    active_type,
):
    api_client.force_authenticate(user=patient_admin_user)

    resp = api_client.get(
        scheduled_patients_url,
        {"procedure_type": active_type.id, "department_id": "abc"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "department_id" in resp.data


@pytest.mark.django_db
def test_admin_filters_by_clinician_id(
    api_client,
    patient_admin_user,
    scheduled_patients_url,
    active_type,
    clinician_a,
    clinician_b,
    patient_1,
    patient_2,
):
    api_client.force_authenticate(user=patient_admin_user)

    p_a = Procedure.objects.create(
        procedure_type=active_type,
        patient=patient_1,
        clinician=clinician_a,
        status="SCHEDULED",
        scheduled_at=timezone.now(),
        duration_minutes=30,
    )
    p_b = Procedure.objects.create(
        procedure_type=active_type,
        patient=patient_2,
        clinician=clinician_b,
        status="SCHEDULED",
        scheduled_at=timezone.now(),
        duration_minutes=30,
    )

    resp_a = api_client.get(
        scheduled_patients_url,
        {
            "procedure_type": active_type.id,
            "clinician": clinician_a.id,
        },
    )
    assert resp_a.status_code == status.HTTP_200_OK
    ids_a = [r["procedure"]["id"] for r in resp_a.data["results"]]
    assert ids_a == [p_a.id]

    resp_b = api_client.get(
        scheduled_patients_url,
        {
            "procedure_type": active_type.id,
            "clinician": clinician_b.id,
        },
    )
    assert resp_b.status_code == status.HTTP_200_OK
    ids_b = [r["procedure"]["id"] for r in resp_b.data["results"]]
    assert ids_b == [p_b.id]


@pytest.mark.django_db
def test_admin_invalid_clinician_id_type_returns_400(
    api_client,
    patient_admin_user,
    scheduled_patients_url,
    active_type,
):
    api_client.force_authenticate(user=patient_admin_user)

    resp = api_client.get(
        scheduled_patients_url,
        {"procedure_type": active_type.id, "clinician": "abc"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "clinician" in resp.data

@pytest.mark.django_db
def test_soft_deleted_procedure_patient_clinician_excluded(
    api_client,
    patient_admin_user,
    scheduled_patients_url,
    active_type,
    clinician_a,
    patient_1,
    patient_2,
):
    api_client.force_authenticate(user=patient_admin_user)

    p_active = Procedure.objects.create(
        procedure_type=active_type,
        patient=patient_1,
        clinician=clinician_a,
        status="SCHEDULED",
        scheduled_at=timezone.now(),
        duration_minutes=30,
    )
    p_deleted = Procedure.objects.create(
        procedure_type=active_type,
        patient=patient_2,
        clinician=clinician_a,
        status="SCHEDULED",
        scheduled_at=timezone.now(),
        duration_minutes=30,
    )
    p_deleted.delete()

    p_soft_patient = Procedure.objects.create(
        procedure_type=active_type,
        patient=patient_2,
        clinician=clinician_a,
        status="SCHEDULED",
        scheduled_at=timezone.now(),
        duration_minutes=30,
    )
    patient_2.delete()

    resp = api_client.get(
        scheduled_patients_url,
        {"procedure_type": active_type.id},
    )
    assert resp.status_code == status.HTTP_200_OK
    ids = [r["procedure"]["id"] for r in resp.data["results"]]

    assert p_active.id in ids
    assert p_deleted.id not in ids
    assert p_soft_patient.id not in ids

@pytest.mark.django_db
def test_clinician_sees_only_own_procedures(
    api_client,
    clinician_user,
    clinician_a,
    clinician_b,
    scheduled_patients_url,
    active_type,
    patient_1,
    patient_2,
):
    api_client.force_authenticate(user=clinician_user)

    p_a = Procedure.objects.create(
        procedure_type=active_type,
        patient=patient_1,
        clinician=clinician_a,
        status="SCHEDULED",
        scheduled_at=timezone.now(),
        duration_minutes=30,
    )
    Procedure.objects.create(
        procedure_type=active_type,
        patient=patient_2,
        clinician=clinician_b,
        status="SCHEDULED",
        scheduled_at=timezone.now(),
        duration_minutes=30,
    )

    resp = api_client.get(
        scheduled_patients_url,
        {"procedure_type": active_type.id},
    )
    assert resp.status_code == status.HTTP_200_OK
    ids = [r["procedure"]["id"] for r in resp.data["results"]]
    assert ids == [p_a.id]


@pytest.mark.django_db
def test_admin_pagination(
    api_client,
    patient_admin_user,
    scheduled_patients_url,
    active_type,
    clinician_a,
    patient_1,
):
    api_client.force_authenticate(user=patient_admin_user)

    # create 5 procedures for same type and clinician
    procs = []
    for i in range(5):
        p = Procedure.objects.create(
            procedure_type=active_type,
            patient=patient_1,
            clinician=clinician_a,
            status="SCHEDULED",
            scheduled_at=timezone.now() + datetime.timedelta(minutes=i),
            duration_minutes=30,
        )
        procs.append(p)

    resp1 = api_client.get(
        scheduled_patients_url,
        {"procedure_type": active_type.id, "limit": 2, "offset": 0},
    )
    assert resp1.status_code == status.HTTP_200_OK
    assert resp1.data["count"] == 5
    assert len(resp1.data["results"]) == 2

    resp2 = api_client.get(
        scheduled_patients_url,
        {"procedure_type": active_type.id, "limit": 2, "offset": 2},
    )
    assert resp2.status_code == status.HTTP_200_OK
    assert resp2.data["count"] == 5
    assert len(resp2.data["results"]) in (2, 1)
