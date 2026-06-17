"""ViewSets и API views для игрового приложения."""

from .admin import (
    AdminCheckView,
    AdminLoginView,
    AdminLogoutView,
    CalculatorCalcView,
    CalculatorResetView,
    CalculatorStateView,
    DocumentDeleteView,
    DocumentDownloadView,
    DocumentView,
    TeamGameView,
    calculator_page,
)
from ..decision_structure import (
    MINISTER_CONTEXT_PARAMS,
    MINISTER_INTERPOLATION_KEYS,
    MINISTER_SHORT_NAMES,
    PARAMETER_TARGETS,
    SUMMARY_GROUP_DEFS,
)
from .game import (
    GameViewSet,
    _normalize_validation_state,
)
from .management import FacultyViewSet, GroupViewSet, TeamViewSet
from .parameters import BatchParameterView, ParameterView, ValidationStateView

__all__ = [
    # Игра
    "GameViewSet",
    "_normalize_validation_state",
    # Константы
    "SUMMARY_GROUP_DEFS",
    "MINISTER_SHORT_NAMES",
    "MINISTER_CONTEXT_PARAMS",
    "MINISTER_INTERPOLATION_KEYS",
    "PARAMETER_TARGETS",
    # Параметры
    "BatchParameterView",
    "ParameterView",
    "ValidationStateView",
    # Администрирование
    "AdminLoginView",
    "AdminLogoutView",
    "AdminCheckView",
    "TeamGameView",
    "DocumentView",
    "DocumentDownloadView",
    "DocumentDeleteView",
    "CalculatorStateView",
    "CalculatorCalcView",
    "CalculatorResetView",
    "calculator_page",
    # Управление (факультеты, группы, команды)
    "FacultyViewSet",
    "GroupViewSet",
    "TeamViewSet",
]
