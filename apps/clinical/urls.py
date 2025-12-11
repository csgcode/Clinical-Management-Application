from rest_framework.routers import DefaultRouter
from django.urls import path

from apps.clinical.views import PatientViewSet, DepartmentClinicianPatientCountView

router = DefaultRouter()

router.register(r"patients", PatientViewSet, basename="patient")


urlpatterns = urlpatterns = [
    *router.urls,
    path(
        "departments/<int:department_id>/clinician-patient-counts/",
        DepartmentClinicianPatientCountView.as_view(),
        name="department-clinician-patient-counts",
    ),
]
