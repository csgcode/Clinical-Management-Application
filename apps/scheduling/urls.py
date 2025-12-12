from rest_framework.routers import DefaultRouter
from django.urls import path, include

from apps.scheduling.views import ProcedureViewSet, ProcedureScheduledPatientsView

router = DefaultRouter()
router.register(r"procedures", ProcedureViewSet, basename="procedure")

urlpatterns = [
    path(
        "procedures/scheduled-patients/",
        ProcedureScheduledPatientsView.as_view(),
        name="procedure-scheduled-patients",
    ),
    path("", include(router.urls)),
]
