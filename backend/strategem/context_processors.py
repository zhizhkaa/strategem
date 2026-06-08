"""Template context flags for environment-specific asset loading."""

from django.conf import settings
from django.http import HttpRequest


def asset_flags(request: HttpRequest) -> dict[str, bool]:
    """Expose frontend asset switches configured in Django settings."""
    return {
        "use_tailwind_cdn": bool(settings.USE_TAILWIND_CDN),
    }
