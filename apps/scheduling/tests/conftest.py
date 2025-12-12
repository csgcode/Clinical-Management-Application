import datetime
import pytest

from django.urls import reverse


from apps.accounts.models import User
from apps.clinical.models import Patient, Clinician, Department
from apps.scheduling.models import ProcedureType


@pytest.fixture
def clinician_a(db, clinician_user, department_a):
    return Clinician.objects.create(
        user=clinician_user,
        department=department_a,
        name="Dr. A",
    )


@pytest.fixture
def clinician_b(db, other_clinician_user, department_b):
    return Clinician.objects.create(
        user=other_clinician_user,
        department=department_b,
        name="Dr. B",
    )


@pytest.fixture
def another_clinician_same_dept(db, department_a):
    return Clinician.objects.create(
        user=User.objects.create_user(
            email="clinician2@example.com",
            password="password123",
        ),
        department=department_a,
        name="Dr. A2",
    )


@pytest.fixture
def active_type(db, department_a):
    return ProcedureType.objects.create(
        name="MRI Brain",
        code="MRI_BRAIN",
        default_duration_minutes=30,
        department=department_a,
        is_active=True,
    )


@pytest.fixture
def other_type(db, department_a):
    return ProcedureType.objects.create(
        name="CT Chest",
        code="CT_CHEST",
        default_duration_minutes=20,
        department=department_a,
        is_active=True,
    )


@pytest.fixture
def inactive_type(db, department_a):
    return ProcedureType.objects.create(
        name="Old Test",
        code="OLD_TEST",
        default_duration_minutes=15,
        department=department_a,
        is_active=False,
    )


@pytest.fixture
def patient_1(db):
    return Patient.objects.create(
        name="Patient One",
        gender=Patient.Gender.FEMALE,
        email="p1@example.com",
        date_of_birth=datetime.date(1990, 1, 1),
    )


@pytest.fixture
def patient_2(db):
    return Patient.objects.create(
        name="Patient Two",
        gender=Patient.Gender.MALE,
        email="p2@example.com",
        date_of_birth=datetime.date(1985, 2, 2),
    )


@pytest.fixture
def patient_3(db):
    return Patient.objects.create(
        name="Patient Three",
        gender=Patient.Gender.OTHER,
        email="p3@example.com",
        date_of_birth=datetime.date(1982, 3, 3),
    )


@pytest.fixture
def scheduled_patients_url():
    return reverse("scheduling:procedure-scheduled-patients")


@pytest.fixture
def patient(db):
    return Patient.objects.create(
        name="Jane Doe",
        gender=Patient.Gender.FEMALE,
        email="jane@example.com",
        date_of_birth=datetime.date(1990, 1, 1),
    )


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


@pytest.fixture
def active_procedure_type(active_type):
    return active_type


@pytest.fixture
def inactive_procedure_type(inactive_type):
    return inactive_type


@pytest.fixture
def procedure_list_url():
    return reverse("scheduling:procedure-list")


@pytest.fixture
def department_a(db, other_department):
    return other_department


@pytest.fixture
def department_b(db, department):
    return department