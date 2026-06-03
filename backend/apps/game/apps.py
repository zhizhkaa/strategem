"""Django application configuration for the game domain."""

from django.apps import AppConfig


class GameConfig(AppConfig):
    """Registers the game app and its display name in Django."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.game"
    verbose_name = "Игра"
