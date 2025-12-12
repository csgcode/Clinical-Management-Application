import datetime

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.clinical.models import Patient, Clinician, Department


@pytest.fixture
def clinician_user_in_dept(db):
    return User.objects.create_user(
        email="doc@example.com",
        password="password123",
    )


@pytest.fixture
def clinician_user_other_dept(db):
    return User.objects.create_user(
        email="otherdoc@example.com",
        password="password123",
    )


@pytest.fixture
def department_a(db):
    return Department.objects.create(name="Cardiology")


@pytest.fixture
def department_b(db):
    return Department.objects.create(name="Neurology")


@pytest.fixture
def clinician_a1(db, clinician_user_in_dept, department_a):
    return Clinician.objects.create(
        user=clinician_user_in_dept,
        department=department_a,
        name="Clinician A1",
    )


@pytest.fixture
def clinician_a2(db, department_a):
    return Clinician.objects.create(
        user=User.objects.create_user(
            email="clinician_a2@example.com",
            password="password123",
        ),
        department=department_a,
        name="Clinician A2",
    )


@pytest.fixture
def clinician_a3(db, department_a):
    return Clinician.objects.create(
        user=User.objects.create_user(
            email="clinician_a3@example.com",
            password="password123",
        ),
        department=department_a,
        name="Clinician A3",
    )


@pytest.fixture
def clinician_b1(db, clinician_user_other_dept, department_b):
    # Logged-in clinician for department B
    return Clinician.objects.create(
        user=clinician_user_other_dept,
        department=department_b,
        name="Clinician B1",
    )


@pytest.fixture
def patient_1(db):
    return Patient.objects.create(
        name="Patient 1",
        gender=Patient.Gender.FEMALE,
        email="p1@example.com",
        date_of_birth=datetime.date(1990, 1, 1),
    )


@pytest.fixture
def patient_2(db):
    return Patient.objects.create(
        name="Patient 2",
        gender=Patient.Gender.MALE,
        email="p2@example.com",
        date_of_birth=datetime.date(1985, 5, 5),
    )


@pytest.fixture
def patient_3(db):
    return Patient.objects.create(
        name="Patient 3",
        gender=Patient.Gender.OTHER,
        email="p3@example.com",
        date_of_birth=datetime.date(1982, 3, 3),
    )


@pytest.fixture
def department_counts_url():
    def _build() -> str:
        return reverse(
            "clinical:clinician-patient-counts",
        )

    return _build
