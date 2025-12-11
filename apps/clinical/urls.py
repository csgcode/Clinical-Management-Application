from rest_framework.routers import DefaultRouter

from apps.clinical.views import PatientViewSet

router = DefaultRouter()
router.register(r"patients", PatientViewSet, basename="patient")

urlpatterns = router.urls
