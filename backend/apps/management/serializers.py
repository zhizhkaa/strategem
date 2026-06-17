"""REST serializers for management directory models."""

from rest_framework import serializers

from .models import Faculty, Group, Team

MIN_TEAM_PASSWORD_LENGTH = 6


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

    access_password = serializers.CharField(required=False, allow_blank=True, write_only=True)
    has_access_password = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = [
            "id",
            "name",
            "group",
            "created_at",
            "updated_at",
            "access_password",
            "has_access_password",
        ]

    def get_has_access_password(self, obj: Team) -> bool:
        return bool(obj.access_password)

    def validate_access_password(self, value: str) -> str:
        password = value.strip()
        if password and len(password) < MIN_TEAM_PASSWORD_LENGTH:
            raise serializers.ValidationError(
                f"Пароль команды должен быть не короче {MIN_TEAM_PASSWORD_LENGTH} символов."
            )
        return password
