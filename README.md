Patientscheduler
================

Quick setup and API notes for the Django project.

Setup with uv
-------------
- Prereqs: Python 3.13 and `uv`.
- Create env: `uv venv && source .venv/bin/activate`
- Install deps: `uv sync`
- Env vars: `cp sample.env .env` (edit as needed)
- Migrate DB: `python manage.py migrate`
- Run server: `python manage.py runserver 0.0.0.0:8000`


## Repository Layout

```
clinicapp/        # Django project (settings, urls, wsgi/asgi)
apps/
  core/           # Core services and reusable models.
  catalog/        
  clinical/       # Users Profiles (models, serializers, filters, API views, urls)
  scheduling/     # Scheduling/Procedures

docker-compose.yml
pyproject.toml
uv.lock
```



Running tests
-------------
- Full suite: `pytest`
- Narrow scope: `pytest tests/apps/clinical` or `pytest -k procedure`

Data model architecture
-----------------------
- Core mixins: `TimeStampedModel` (`created_at`, `updated_at`), `SoftDeleteModel` (`deleted_at` + manager).
- Department: hospital department (`name`, `description`, `is_active`).
- Clinician: one-to-one `User`, belongs to `Department`; soft-deletable.
- Patient: optional one-to-one `User`; fields `name`, `gender`, `email`, `date_of_birth`; M2M to Clinician via `PatientClinician`.
- PatientClinician: through model with `is_primary`, `relationship_start/relationship_end`, soft delete; unique per `(patient, clinician, relationship_start)`.
- ProcedureType: catalogue entry with `name`, unique `code`, optional `default_duration_minutes` and `Department`, `is_active`.
- Procedure: links `ProcedureType` + `Patient` + `Clinician`; fields `name` (defaults to type), `scheduled_at`, `duration_minutes`, `status` (planned/scheduled/completed/cancelled/no_show/void), `notes`; soft deletable.

API endpoints (prefix `/api/v1/`)
---------------------------------
- Patients CRUD: `/patients/` (list/create, `?search=` by name/email), `/patients/{id}/` (retrieve/update/delete).
  ```json
  {
    "name": "Jane Doe",
    "gender": "FEMALE",
    "email": "jane@example.com",
    "date_of_birth": "1990-04-12"
  }
  ```
- Assign procedure: `POST /procedures/`
  ```json
  {
    "procedure_type_id": 1,
    "patient_id": 10,
    "clinician_id": 3,
    "scheduled_at": "2025-01-15T09:00:00Z",
    "duration_minutes": 45,
    "status": "PLANNED",
    "notes": "Pre-op check"
  }
  ```
  Response example:
  ```json
  {
    "id": 42,
    "procedure_type": {"id": 1, "name": "MRI"},
    "patient": {"id": 10, "name": "Jane Doe"},
    "clinician": {"id": 3, "name": "Dr. Smith"},
    "name": "MRI",
    "scheduled_at": "2025-01-15T09:00:00Z",
    "duration_minutes": 45,
    "status": "PLANNED",
    "notes": "",
    "created_at": "...",
    "updated_at": "..."
  }
  ```
- Clinician patient counts: `GET /clinician-patient-counts/?department=1` (optional `clinician`).
  ```json
  [
    {"id": 3, "name": "Dr. Smith", "department": 1, "patient_count": 12}
  ]
  ```
- Scheduled patients by procedure type: `GET /scheduling/procedures/scheduled-patients/?procedure_type_id=1&date_from=2025-01-01&date_to=2025-01-31`
  ```json
  {
    "procedure": {
      "id": 42,
      "status": "SCHEDULED",
      "scheduled_at": "2025-01-15T09:00:00Z",
      "duration_minutes": 45
    },
    "patient": {"id": 10, "name": "Jane Doe", "gender": "FEMALE"},
    "clinician": {"id": 3, "name": "Dr. Smith"}
  }
  ```
