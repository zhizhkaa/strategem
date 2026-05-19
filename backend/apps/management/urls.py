from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    FacultyViewSet,
    GroupViewSet,
    TeamViewSet,
)

router = DefaultRouter()
router.register("faculties", FacultyViewSet)
router.register("groups", GroupViewSet)
router.register("teams", TeamViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
