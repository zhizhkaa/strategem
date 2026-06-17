"""
URL маршруты для API игры Стратегема.

Включает маршруты для:
- Факультетов, групп и команд
- Игр и их состояния
- Параметров игры
- Административных функций
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminCheckView,
    AdminLoginView,
    AdminLogoutView,
    BatchParameterView,
    CalculatorCalcView,
    CalculatorResetView,
    CalculatorStateView,
    DocumentDeleteView,
    DocumentDownloadView,
    DocumentView,
    FacultyViewSet,
    GameViewSet,
    GroupViewSet,
    ParameterView,
    TeamGameView,
    TeamViewSet,
    ValidationStateView,
)

# Создаём роутер для ViewSets
router = DefaultRouter()
router.register(r"faculties", FacultyViewSet, basename="faculty")
router.register(r"groups", GroupViewSet, basename="group")
router.register(r"teams", TeamViewSet, basename="team")
router.register(r"games", GameViewSet, basename="game")

urlpatterns = [
    # ViewSets через роутер
    path("", include(router.urls)),
    # Пакетное обновление параметров (должен быть ДО <str:param>, иначе "batch" захватится как param)
    # POST /api/games/{game_id}/parameters/batch/ - пакетное обновление
    path(
        "games/<int:game_id>/parameters/batch/",
        BatchParameterView.as_view(),
        name="batch-parameter",
    ),
    # Параметры игры
    # GET /api/games/{game_id}/parameters/{param}/ - получить параметр
    # POST /api/games/{game_id}/parameters/{param}/ - установить параметр
    path(
        "games/<int:game_id>/parameters/<str:param>/",
        ParameterView.as_view(),
        name="game-parameter",
    ),
    # Игра команды
    # GET /api/teams/{team_id}/game/ - получить игру команды
    path(
        "teams/<int:team_id>/game/",
        TeamGameView.as_view(),
        name="team-game",
    ),
    # Состояние валидации (лёгкий polling-эндпоинт)
    # GET /api/games/{game_id}/validation/ - текущие ошибки и незаполненные параметры
    path(
        "games/<int:game_id>/validation/",
        ValidationStateView.as_view(),
        name="game-validation",
    ),
    # Административные эндпоинты
    path("admin/login/", AdminLoginView.as_view(), name="admin-login"),
    path("admin/logout/", AdminLogoutView.as_view(), name="admin-logout"),
    path("admin/check/", AdminCheckView.as_view(), name="admin-check"),
    # Калькулятор (отладочная страница)
    path("admin/calculator/<int:game_id>/state/", CalculatorStateView.as_view(), name="calculator-state"),
    path("admin/calculator/<int:game_id>/calculate/", CalculatorCalcView.as_view(), name="calculator-calc"),
    path("admin/calculator/<int:game_id>/reset/", CalculatorResetView.as_view(), name="calculator-reset"),
    # Документация
    # GET /api/documents/         - список файлов
    # POST /api/documents/        - загрузить файл (admin)
    path("documents/", DocumentView.as_view(), name="documents"),
    # GET /api/documents/{id}/download/ - скачать файл
    path(
        "documents/<int:doc_id>/download/",
        DocumentDownloadView.as_view(),
        name="document-download",
    ),
    # DELETE /api/documents/{id}/ - удалить файл (admin)
    path("documents/<int:doc_id>/", DocumentDeleteView.as_view(), name="document-delete"),
]
