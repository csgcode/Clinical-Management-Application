from rest_framework.routers import DefaultRouter
from django.urls import include, path

from apps.clinical.views import PatientViewSet, DepartmentClinicianPatientCountListViewSet

router = DefaultRouter()

router.register(r"patients", PatientViewSet, basename="patient")


urlpatterns = urlpatterns = [
    path("", include(router.urls)),
    path("departments/<int:department_id>/clinician-patient-counts/",
        DepartmentClinicianPatientCountListViewSet.as_view(),
        name="department-clinician-patient-counts",
    ),
]
