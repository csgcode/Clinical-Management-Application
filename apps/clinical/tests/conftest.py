import datetime

import pytest
from django.contrib.auth.models import Group, Permission
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.clinical.models import Patient, Clinician, PatientClinician, Department


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
            "add_patient",
            "change_patient",
            "delete_patient",
            "view_patient",
        ],
    )
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
def clinician_user(db):
    user = User.objects.create_user(
        email="doc@example.com",
        password="password123",
        is_staff=False,
    )
    return user


@pytest.fixture
def department(db):
    return Department.objects.create(name="Cardiology")


@pytest.fixture
def clinician_profile(db, clinician_user, department):
    return Clinician.objects.create(
        user=clinician_user,
        department=department,
        name="Dr. Strange",
    )


@pytest.fixture
def other_clinician_user(db):
    user = User.objects.create_user(
        email="otherdoc@example.com",
        password="password123",
        is_staff=False,
    )
    return user


@pytest.fixture
def other_clinician_profile(db, other_clinician_user, department):
    return Clinician.objects.create(
        user=other_clinician_user,
        department=department,
        name="Dr. House",
    )


@pytest.fixture
def active_patient(db):
    return Patient.objects.create(
        name="Jane Doe",
        gender=Patient.Gender.FEMALE,
        email="jane@example.com",
        date_of_birth=datetime.date(1990, 1, 1),
    )


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
def linked_patient(db, clinician_profile):
    patient = Patient.objects.create(
        name="Linked Patient",
        gender=Patient.Gender.FEMALE,
        email="linked@example.com",
        date_of_birth=datetime.date(1992, 7, 12),
    )
    PatientClinician.objects.create(
        patient=patient,
        clinician=clinician_profile,
        is_primary=True,
        relationship_start=datetime.datetime.now(datetime.timezone.utc),
    )
    return patient


@pytest.fixture
def unlinked_patient(db):
    return Patient.objects.create(
        name="Unlinked Patient",
        gender=Patient.Gender.FEMALE,
        email="unlinked@example.com",
        date_of_birth=datetime.date(1993, 3, 3),
    )
