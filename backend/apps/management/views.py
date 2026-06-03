"""API endpoints for faculties, groups, and teams."""

from rest_framework import viewsets

from .models import Faculty, Group, Team
from .serializers import FacultySerializer, GroupSerializer, TeamSerializer


class FacultyViewSet(viewsets.ModelViewSet):
    """CRUD API for faculties."""

    queryset = Faculty.objects.all()
    serializer_class = FacultySerializer


class GroupViewSet(viewsets.ModelViewSet):
    """CRUD API for student groups."""

    queryset = Group.objects.all()
    serializer_class = GroupSerializer


class TeamViewSet(viewsets.ModelViewSet):
    """CRUD API for teams."""

    queryset = Team.objects.all()
    serializer_class = TeamSerializer
