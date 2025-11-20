from django.urls import include, path
from rest_framework.routers import DefaultRouter

from ai.views import AICaptionJobViewSet

app_name = "ai"

router = DefaultRouter()
router.register(r"caption-jobs", AICaptionJobViewSet, basename="captionjob")

urlpatterns = [
    path("", include(router.urls)),
]
