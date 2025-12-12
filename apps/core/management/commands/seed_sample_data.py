"""
Django management command to seed sample data into the database.

Run with: python manage.py seed_sample_data
"""

import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from apps.accounts.models import User
from apps.clinical.models import Department, Clinician, Patient, PatientClinician
from apps.catalog.models import ProcedureType
from apps.scheduling.models import Procedure


class Command(BaseCommand):
    help = "Seed the database with sample data for all models"

    def handle(self, *args, **options):
        self.stdout.write("Starting sample data seeding...")

        seed_users()
        seed_groups_and_permissions()
        seed_departments()
        seed_clinicians()
        seed_patients()
        seed_patient_clinician_links()
        seed_procedure_types()
        seed_procedures()

        self.stdout.write(self.style.SUCCESS("Sample data seeded successfully!"))


def seed_users():
    """Create sample user accounts."""
    users = [
        {
            "email": "admin@hospital.com",
            "password": "admin123",
            "is_staff": True,
            "is_superuser": True,
        },
        {
            "email": "dr.smith@hospital.com",
            "password": "clinician123",
            "is_staff": True,
            "is_superuser": False,
        },
        {
            "email": "dr.jones@hospital.com",
            "password": "clinician123",
            "is_staff": True,
            "is_superuser": False,
        },
        {
            "email": "dr.williams@hospital.com",
            "password": "clinician123",
            "is_staff": True,
            "is_superuser": False,
        },
        {
            "email": "patient1@example.com",
            "password": "patient123",
            "is_staff": False,
            "is_superuser": False,
        },
        {
            "email": "patient2@example.com",
            "password": "patient123",
            "is_staff": False,
            "is_superuser": False,
        },
    ]

    for user_data in users:
        email = user_data.pop("email")
        password = user_data.pop("password")
        user, created = User.objects.get_or_create(
            email=email,
            defaults=user_data,
        )
        if created:
            user.set_password(password)
            user.save()

    print("Created sample users")


def seed_groups_and_permissions():
    """Create sample user groups with permissions."""
    patient_admin_group, _ = Group.objects.get_or_create(name="patient_admin")
    clinician_group, _ = Group.objects.get_or_create(name="clinician")

    patient_content_type = ContentType.objects.get(
        app_label="clinical", model="patient"
    )
    patient_perms = Permission.objects.filter(
        content_type=patient_content_type,
        codename__in=[
            "add_patient",
            "change_patient",
            "delete_patient",
            "view_patient",
        ],
    )
    patient_admin_group.permissions.set(patient_perms)

    procedure_content_type = ContentType.objects.get(
        app_label="scheduling", model="procedure"
    )
    procedure_perms = Permission.objects.filter(
        content_type=procedure_content_type,
        codename__in=["add_procedure", "change_procedure", "view_procedure"],
    )
    clinician_group.permissions.set(procedure_perms)

    admin_user = User.objects.get(email="admin@hospital.com")
    admin_user.groups.add(patient_admin_group)

    print("Created sample groups and permissions")


def seed_departments():
    """Create sample departments."""
    departments = [
        {"name": "Cardiology", "description": "Heart and cardiovascular diseases"},
        {"name": "Radiology", "description": "Medical imaging and diagnostics"},
        {"name": "Neurology", "description": "Brain and nervous system"},
        {"name": "Orthopedics", "description": "Bone and joint care"},
    ]

    for dept_data in departments:
        Department.objects.get_or_create(**dept_data)

    print("Created sample departments")


def seed_clinicians():
    """Create sample clinician profiles."""
    clinicians = [
        {
            "user_email": "dr.smith@hospital.com",
            "name": "Dr. James Smith",
            "department_name": "Cardiology",
        },
        {
            "user_email": "dr.jones@hospital.com",
            "name": "Dr. Sarah Jones",
            "department_name": "Radiology",
        },
        {
            "user_email": "dr.williams@hospital.com",
            "name": "Dr. Robert Williams",
            "department_name": "Neurology",
        },
    ]

    for clinic_data in clinicians:
        user_email = clinic_data.pop("user_email")
        dept_name = clinic_data.pop("department_name")

        user = User.objects.get(email=user_email)
        department = Department.objects.get(name=dept_name)

        clinician, _ = Clinician.objects.get_or_create(
            user=user,
            defaults={
                "name": clinic_data["name"],
                "department": department,
            },
        )
        user.groups.add(Group.objects.get(name="clinician"))

    print("Created sample clinicians")


def seed_patients():
    """Create sample patient profiles."""
    patients = [
        {
            "name": "John Brown",
            "gender": Patient.Gender.MALE,
            "email": "john.brown@example.com",
            "date_of_birth": datetime.date(1975, 5, 15),
        },
        {
            "name": "Emma Davis",
            "gender": Patient.Gender.FEMALE,
            "email": "emma.davis@example.com",
            "date_of_birth": datetime.date(1982, 8, 22),
        },
        {
            "name": "Michael Wilson",
            "gender": Patient.Gender.MALE,
            "email": "michael.wilson@example.com",
            "date_of_birth": datetime.date(1968, 3, 10),
        },
        {
            "name": "Lisa Anderson",
            "gender": Patient.Gender.FEMALE,
            "email": "lisa.anderson@example.com",
            "date_of_birth": datetime.date(1990, 11, 5),
        },
        {
            "name": "James Taylor",
            "gender": Patient.Gender.MALE,
            "email": "james.taylor@example.com",
            "date_of_birth": datetime.date(1958, 6, 30),
        },
    ]

    for patient_data in patients:
        Patient.objects.get_or_create(**patient_data)

    print("Created sample patients")


def seed_patient_clinician_links():
    """Create sample relationships between patients and clinicians."""
    links = [
        {"patient_name": "John Brown", "clinician_name": "Dr. James Smith"},
        {"patient_name": "Emma Davis", "clinician_name": "Dr. Sarah Jones"},
        {"patient_name": "Michael Wilson", "clinician_name": "Dr. Robert Williams"},
        {"patient_name": "Lisa Anderson", "clinician_name": "Dr. James Smith"},
        {"patient_name": "James Taylor", "clinician_name": "Dr. Sarah Jones"},
    ]

    now = timezone.now()
    for link_data in links:
        patient = Patient.objects.get(name=link_data["patient_name"])
        clinician = Clinician.objects.get(name=link_data["clinician_name"])

        PatientClinician.objects.get_or_create(
            patient=patient,
            clinician=clinician,
            defaults={
                "is_primary": True,
                "relationship_start": now,
                "relationship_end": None,
            },
        )

    print("Created sample patient-clinician links")


def seed_procedure_types():
    """Create sample procedure types."""
    procedure_types = [
        {
            "name": "Echocardiogram",
            "code": "ECG",
            "default_duration_minutes": 45,
            "department_name": "Cardiology",
            "is_active": True,
        },
        {
            "name": "Coronary Angiography",
            "code": "CATH",
            "default_duration_minutes": 90,
            "department_name": "Cardiology",
            "is_active": True,
        },
        {
            "name": "MRI Brain",
            "code": "MRI_BRAIN",
            "default_duration_minutes": 60,
            "department_name": "Radiology",
            "is_active": True,
        },
        {
            "name": "X-Ray Chest",
            "code": "XRAY_CHEST",
            "default_duration_minutes": 15,
            "department_name": "Radiology",
            "is_active": True,
        },
        {
            "name": "CT Head",
            "code": "CT_HEAD",
            "default_duration_minutes": 30,
            "department_name": "Radiology",
            "is_active": True,
        },
        {
            "name": "EEG",
            "code": "EEG",
            "default_duration_minutes": 60,
            "department_name": "Neurology",
            "is_active": True,
        },
        {
            "name": "MRI Spine",
            "code": "MRI_SPINE",
            "default_duration_minutes": 75,
            "department_name": "Neurology",
            "is_active": True,
        },
        {
            "name": "X-Ray Knee",
            "code": "XRAY_KNEE",
            "default_duration_minutes": 20,
            "department_name": "Orthopedics",
            "is_active": True,
        },
    ]

    for proc_type_data in procedure_types:
        dept_name = proc_type_data.pop("department_name")
        department = Department.objects.get(name=dept_name)

        ProcedureType.objects.get_or_create(
            code=proc_type_data["code"],
            defaults={
                "name": proc_type_data["name"],
                "default_duration_minutes": proc_type_data["default_duration_minutes"],
                "department": department,
                "is_active": proc_type_data["is_active"],
            },
        )

    print("Created sample procedure types")


def seed_procedures():
    """Create sample procedures."""
    procedures = [
        {
            "patient_name": "John Brown",
            "clinician_name": "Dr. James Smith",
            "procedure_type_code": "ECG",
            "scheduled_at": timezone.now() + datetime.timedelta(days=1),
            "status": "PLANNED",
            "duration_minutes": 45,
        },
        {
            "patient_name": "Emma Davis",
            "clinician_name": "Dr. Sarah Jones",
            "procedure_type_code": "MRI_BRAIN",
            "scheduled_at": timezone.now() + datetime.timedelta(days=2),
            "status": "SCHEDULED",
            "duration_minutes": 60,
        },
        {
            "patient_name": "Michael Wilson",
            "clinician_name": "Dr. Robert Williams",
            "procedure_type_code": "EEG",
            "scheduled_at": timezone.now() + datetime.timedelta(days=3),
            "status": "PLANNED",
            "duration_minutes": 60,
        },
        {
            "patient_name": "Lisa Anderson",
            "clinician_name": "Dr. James Smith",
            "procedure_type_code": "CATH",
            "scheduled_at": timezone.now() + datetime.timedelta(days=4),
            "status": "SCHEDULED",
            "duration_minutes": 90,
        },
        {
            "patient_name": "James Taylor",
            "clinician_name": "Dr. Sarah Jones",
            "procedure_type_code": "CT_HEAD",
            "scheduled_at": timezone.now() + datetime.timedelta(days=5),
            "status": "PLANNED",
            "duration_minutes": 30,
        },
    ]

    for proc_data in procedures:
        patient = Patient.objects.get(name=proc_data["patient_name"])
        clinician = Clinician.objects.get(name=proc_data["clinician_name"])
        procedure_type = ProcedureType.objects.get(
            code=proc_data["procedure_type_code"]
        )

        Procedure.objects.get_or_create(
            patient=patient,
            clinician=clinician,
            procedure_type=procedure_type,
            scheduled_at=proc_data["scheduled_at"],
            defaults={
                "status": proc_data["status"],
                "duration_minutes": proc_data["duration_minutes"],
            },
        )

    print("Created sample procedures")
