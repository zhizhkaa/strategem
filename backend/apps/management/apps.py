from django.apps import AppConfig


class ManagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    verbose_name = "Управление командами"
    name = "apps.management"
