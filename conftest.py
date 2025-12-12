"""
Shared pytest fixtures for all tests in the application.

These fixtures provide common test data and API clients that are
reused across multiple test modules to eliminate duplication.
"""

import datetime

import pytest
from django.contrib.auth.models import Group, Permission
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.clinical.models import Patient, Clinician, Department, PatientClinician


@pytest.fixture
def api_client():
    """
    Provides a DRF APIClient for making API requests in tests.

    Returns:
        APIClient instance
    """
    return APIClient()


@pytest.fixture
def patient_admin_group(db):
    """
    Creates or gets the 'patient_admin' group with appropriate permissions.

    Args:
        db: pytest-django database fixture

    Returns:
        Group instance for patient_admin role
    """
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
    """
    Creates a patient admin user in the patient_admin group.

    Args:
        db: pytest-django database fixture
        patient_admin_group: The patient_admin group fixture

    Returns:
        User instance with patient_admin group membership
    """
    user = User.objects.create_user(
        email="admin@example.com",
        password="password123",
        is_staff=True,
    )
    user.groups.add(patient_admin_group)
    return user


@pytest.fixture
def regular_user(db):
    """
    Creates a regular user with no group memberships.

    Args:
        db: pytest-django database fixture

    Returns:
        User instance with no special roles
    """
    return User.objects.create_user(
        email="regular@example.com",
        password="password123",
    )


@pytest.fixture
def clinician_user(db):
    """
    Creates a clinician user (authenticated but without clinician_profile yet).

    Args:
        db: pytest-django database fixture

    Returns:
        User instance for clinician role
    """
    return User.objects.create_user(
        email="doc@example.com",
        password="password123",
        is_staff=False,
    )


@pytest.fixture
def other_clinician_user(db):
    """
    Creates another clinician user for testing multi-clinician scenarios.

    Args:
        db: pytest-django database fixture

    Returns:
        User instance for second clinician
    """
    return User.objects.create_user(
        email="otherdoc@example.com",
        password="password123",
        is_staff=False,
    )


@pytest.fixture
def department(db):
    """
    Creates a test department.

    Args:
        db: pytest-django database fixture

    Returns:
        Department instance
    """
    return Department.objects.create(name="Cardiology")


@pytest.fixture
def other_department(db):
    """
    Creates a second test department for multi-department scenarios.

    Args:
        db: pytest-django database fixture

    Returns:
        Department instance
    """
    return Department.objects.create(name="Radiology")


@pytest.fixture
def clinician_profile(db, clinician_user, department):
    """
    Creates a clinician profile linked to a user and department.

    Args:
        db: pytest-django database fixture
        clinician_user: The clinician user fixture
        department: The department fixture

    Returns:
        Clinician instance
    """
    return Clinician.objects.create(
        user=clinician_user,
        department=department,
        name="Dr. Strange",
    )


@pytest.fixture
def other_clinician_profile(db, other_clinician_user, department):
    """
    Creates a second clinician profile for multi-clinician scenarios.

    Args:
        db: pytest-django database fixture
        other_clinician_user: The second clinician user fixture
        department: The department fixture

    Returns:
        Clinician instance
    """
    return Clinician.objects.create(
        user=other_clinician_user,
        department=department,
        name="Dr. House",
    )


@pytest.fixture
def active_patient(db):
    """
    Creates a test patient.

    Args:
        db: pytest-django database fixture

    Returns:
        Patient instance
    """
    return Patient.objects.create(
        name="Jane Doe",
        gender=Patient.Gender.FEMALE,
        email="jane@example.com",
        date_of_birth=datetime.date(1990, 1, 1),
    )


@pytest.fixture
def another_patient(db):
    """
    Creates a second test patient for multi-patient scenarios.

    Args:
        db: pytest-django database fixture

    Returns:
        Patient instance
    """
    return Patient.objects.create(
        name="John Smith",
        gender=Patient.Gender.MALE,
        email="john.smith@example.com",
        date_of_birth=datetime.date(1985, 5, 5),
    )


@pytest.fixture
def soft_deleted_patient(db):
    """
    Creates a test patient and soft-deletes it.

    Args:
        db: pytest-django database fixture

    Returns:
        Soft-deleted Patient instance
    """
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
    """
    Creates a patient with an active link to a clinician.

    Args:
        db: pytest-django database fixture
        clinician_profile: The clinician profile fixture

    Returns:
        Patient instance with active PatientClinician link
    """
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
    """
    Creates a patient with no clinician links.

    Args:
        db: pytest-django database fixture

    Returns:
        Patient instance with no PatientClinician links
    """
    return Patient.objects.create(
        name="Unlinked Patient",
        gender=Patient.Gender.FEMALE,
        email="unlinked@example.com",
        date_of_birth=datetime.date(1993, 3, 3),
    )
