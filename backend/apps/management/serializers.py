"""REST serializers for management directory models."""

from rest_framework import serializers

from .models import Faculty, Group, Team


class FacultySerializer(serializers.ModelSerializer):
    """Serializes faculty records."""

    class Meta:
        model = Faculty
        fields = "__all__"


class GroupSerializer(serializers.ModelSerializer):
    """Serializes student group records."""

    class Meta:
        model = Group
        fields = "__all__"


class TeamSerializer(serializers.ModelSerializer):
    """Serializes team records."""

    class Meta:
        model = Team
        fields = "__all__"
