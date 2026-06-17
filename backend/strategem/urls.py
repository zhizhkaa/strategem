"""
URL configuration for strategem project.

Маршруты:
- /api/ - REST API для игры
- /api/docs/ - Swagger документация
- / - Главная страница (фронтенд)
- /game/ - Экран игры
- /admin-panel/ - Панель администратора
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.urls import include, path
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.game.views import calculator_page


# Views с CSRF cookie для страниц с формами
@ensure_csrf_cookie
def index_view(request):
    """Главная страница - выбор команды."""
    return render(request, "index.html")


@ensure_csrf_cookie
def game_view(request):
    """Экран игры."""
    return render(request, "game/play.html")


@ensure_csrf_cookie
def admin_panel_view(request):
    """Панель администратора."""
    return render(request, "admin/panel.html")


@ensure_csrf_cookie
def admin_login_view(request):
    """Вход администратора."""
    return render(request, "admin/login.html")


@ensure_csrf_cookie
def charts_view(request):
    """Страница графиков."""
    return render(request, "game/charts.html")


@ensure_csrf_cookie
def game_results_view(request):
    """Страница результатов завершённой игры."""
    return render(request, "game/results.html")


@ensure_csrf_cookie
def minister_view(request, minister_key):
    """Страница министра — лист решений."""
    return render(request, "game/minister.html", {"minister_key": minister_key})


@ensure_csrf_cookie
def review_view(request):
    """Сводный лист решений."""
    return render(request, "game/review.html")


@ensure_csrf_cookie
def admin_game_status_view(request, game_id):
    """Состояние страны для конкретной игры (из admin-панели)."""
    return render(request, "game/status.html", {"game_id": game_id})


@ensure_csrf_cookie
def docs_view(request):
    """Страница документации — список файлов для игроков."""
    return render(request, "game/docs.html")


def admin_session_required(view_func):
    """Закрывает служебные страницы от игроков без админской сессии."""

    def wrapped(request, *args, **kwargs):
        if not request.session.get("is_admin", False):
            return HttpResponseForbidden("Доступно только администратору")
        return view_func(request, *args, **kwargs)

    return wrapped


urlpatterns = [
    # ========================================
    # DJANGO ADMIN (стандартная админка)
    # ========================================
    path("django-admin/", admin.site.urls),
    # ========================================
    # API ENDPOINTS
    # ========================================
    # Основной API игры
    path("api/", include("apps.game.urls")),
    # API управления (факультеты, группы, команды)
    path("api/management/", include("apps.management.urls")),
    # OpenAPI Schema
    path(
        "api/schema/",
        admin_session_required(SpectacularAPIView.as_view()),
        name="schema",
    ),
    # Swagger UI
    path(
        "api/docs/",
        admin_session_required(SpectacularSwaggerView.as_view(url_name="schema")),
        name="swagger-ui",
    ),
    # ========================================
    # FRONTEND VIEWS (Django Templates с CSRF)
    # ========================================
    # Главная страница - выбор команды
    path("", index_view, name="index"),
    # Экран игры
    path("game/", game_view, name="game"),
    # Панель администратора
    path("admin-panel/", admin_panel_view, name="admin-panel"),
    # Калькулятор (отладочная страница)
    path("admin-panel/calculator/", calculator_page, name="calculator-page"),
    # Вход администратора
    path("admin-login/", admin_login_view, name="admin-login"),
    # Графики
    path("charts/", charts_view, name="charts"),
    # Результаты игры
    path("game-results/", game_results_view, name="game-results"),
    # Листы министров (Excel-интерфейс)
    path("game/minister/<str:minister_key>/", minister_view, name="minister"),
    # Сводный лист решений
    path("game/review/", review_view, name="review"),
    # Состояние страны (из admin-панели)
    path("admin/game/<int:game_id>/status/", admin_game_status_view, name="admin-game-status"),
    # Документация для игроков
    path("game/docs/", docs_view, name="game-docs"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
