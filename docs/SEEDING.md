# Sample Data Seeding

This directory contains Django management commands for seeding the database with sample data for testing and development.

## Management Commands

### `seed_sample_data`

Populates the database with realistic sample data for all models.

**Usage:**

```bash
python manage.py seed_sample_data
```

**What it creates:**

#### Users (8 total)
- 1 superadmin user
- 3 clinician users (Dr. Smith, Dr. Jones, Dr. Williams)
- 2 patient users
- 2 additional test users

**Credentials:**
- Admin: `admin@hospital.com` / `admin123`
- Clinician: `dr.smith@hospital.com` / `clinician123`
- Patient: `patient1@example.com` / `patient123`

#### Departments (4)
- Cardiology
- Radiology
- Neurology
- Orthopedics

#### Clinicians (3)
- Dr. James Smith (Cardiology)
- Dr. Sarah Jones (Radiology)
- Dr. Robert Williams (Neurology)

#### Patients (5)
- John Brown
- Emma Davis
- Michael Wilson
- Lisa Anderson
- James Taylor

#### Patient-Clinician Relationships (5)
- Active (ongoing) relationships between patients and clinicians

#### Procedure Types (8)
- Cardiology: Echocardiogram, Coronary Angiography
- Radiology: MRI Brain, X-Ray Chest, CT Head
- Neurology: EEG, MRI Spine
- Orthopedics: X-Ray Knee

#### Procedures (5)
- Sample procedures scheduled over the next 5 days
- Mix of PLANNED and SCHEDULED statuses

## Running the seeder

After migrations are applied:

```bash
python manage.py seed_sample_data
```

The command will:
1. Create users with proper password hashing
2. Create groups and assign permissions
3. Create departments
4. Create clinician profiles linked to users and departments
5. Create patient profiles
6. Create relationships between patients and clinicians
7. Create procedure type catalogue
8. Create sample procedures scheduled for patients

## Testing the seeded data

You can verify the seeded data in the Django shell:

```bash
python manage.py shell
```

Then:

```python
from apps.accounts.models import User
from apps.clinical.models import Department, Patient, Clinician
from apps.catalog.models import ProcedureType
from apps.scheduling.models import Procedure

print(f"Users: {User.objects.count()}")
print(f"Patients: {Patient.objects.count()}")
print(f"Departments: {Department.objects.count()}")
print(f"Procedure Types: {ProcedureType.objects.count()}")
print(f"Procedures: {Procedure.objects.count()}")

# Get a specific user
admin = User.objects.get(email="admin@hospital.com")
print(f"Admin: {admin}")

# List all patients
for patient in Patient.objects.all():
    print(f"  - {patient.name}")
```

## Idempotency

The seeder is idempotent — running it multiple times will not create duplicate data. It uses `get_or_create()` to check for existing records before creating new ones.

## Resetting the database

To start fresh and clear all data:

```bash
python manage.py flush  # WARNING: Deletes ALL data
python manage.py seed_sample_data  # Reseed
```

## Notes

- Sample data includes a mix of active and non-active records.
- Soft-deleted models are handled by the `SoftDeleteModel` base class.
- Timestamps (`created_at`, `updated_at`) are automatically managed by Django.
- All relationships (ForeignKey, OneToOne) are properly linked.
