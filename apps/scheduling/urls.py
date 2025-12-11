# apps/scheduling/api/urls.py
from rest_framework.routers import DefaultRouter

from apps.scheduling.views import ProcedureViewSet

router = DefaultRouter()
router.register(r"procedures", ProcedureViewSet, basename="procedure")

urlpatterns = router.urls
