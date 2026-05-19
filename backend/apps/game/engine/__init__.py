"""
Game Engine Module

Движок игры Стратегема, включающий:
- calculator: расчёт формул и переход между периодами
- interpolation: линейная интерполяция по таблицам
- validator: валидация формул и параметров
- state_manager: управление состоянием игры
"""

from .calculator import GameCalculator, get_calculator
from .interpolation import Interpolator
from .state_manager import GameStateManager, get_state_manager
from .validator import FormulaValidator

__all__ = [
    "Interpolator",
    "FormulaValidator",
    "GameCalculator",
    "GameStateManager",
    "get_calculator",
    "get_state_manager",
]
