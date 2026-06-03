"""Django application configuration for team management."""

from django.apps import AppConfig


class ManagementConfig(AppConfig):
    """Registers management models and their admin-facing app label."""

    default_auto_field = "django.db.models.BigAutoField"
    verbose_name = "Управление командами"
    name = "apps.management"
