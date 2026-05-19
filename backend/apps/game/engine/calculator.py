"""
Движок расчётов игры Стратегема
"""

import logging
import re
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
from statistics import mean
from typing import Any, Optional

import yaml
from simpleeval import SimpleEval

from .interpolation import get_interpolator

logger = logging.getLogger(__name__)


class GameCalculator:
    """
    Калькулятор, выполняющий расчёты

    Загружает формулы из .yaml файла и предоставляет методы
    для вычисления параметров и перехода между периодами
    """

    def __init__(self):
        self._formulas: dict = {}
        self._decision_order: dict = {}
        self._parameters_config: dict = {}
        self._initial_profiles: dict = {}
        self._resolved_profile_configs: dict[str, dict[str, Any]] = {}
        self._interpolator = get_interpolator()
        self._load_config()

    def _load_config(self) -> None:
        """Загружает конфигурацию из .yaml файлов"""
        data_dir = Path(__file__).parent.parent / "data"
        self._formulas = {}
        self._decision_order = {}
        self._parameters_config = {}
        self._initial_profiles = {}
        self._resolved_profile_configs = {}

        # Загружаем формулы
        formulas_path = data_dir / "formulas.yaml"
        if formulas_path.exists():
            with open(formulas_path, "r", encoding="utf-8") as f:
                self._formulas = yaml.safe_load(f) or {}

        # Загружаем порядок решений
        order_path = data_dir / "decision_order.yaml"
        if order_path.exists():
            with open(order_path, "r", encoding="utf-8") as f:
                self._decision_order = yaml.safe_load(f) or {}

        # Загружаем конфигурацию параметров
        params_path = data_dir / "parameters.yaml"
        if params_path.exists():
            with open(params_path, "r", encoding="utf-8") as f:
                params_data = yaml.safe_load(f) or {}
                for category in params_data.values():
                    if isinstance(category, dict):
                        self._parameters_config.update(category)

        profiles_path = data_dir / "difficulties.yaml"
        if profiles_path.exists():
            with open(profiles_path, "r", encoding="utf-8") as f:
                self._initial_profiles = yaml.safe_load(f) or {}

    def reload_config(self) -> None:
        self._load_config()
        self._interpolator.reload_tables()

    def get_calculation_order(self) -> list[str]:
        """Возвращает порядок расчётов"""
        return self._decision_order.get("calculation_order", [])

    def get_decision_stages(self) -> dict:
        """Возвращает этапы принятия решений"""
        stages = {}
        for key, value in self._decision_order.items():
            if isinstance(value, dict) and "order" in value:
                stages[key] = value
        return dict(sorted(stages.items(), key=lambda x: x[1].get("order", 999)))

    def calculate_next_period(
        self,
        current_params: dict[str, float],
        history: list[dict[str, float]],
        recalculate_decisions: bool = True,
    ) -> dict[str, float]:
        """
        Рассчитывает параметры для следующего периода.

        Args:
            current_params: Текущие параметры (с решениями игроков)
            history: История параметров за предыдущие периоды

        Returns:
            Словарь с рассчитанными параметрами для нового периода
        """
        # Создаём копию параметров для нового периода
        new_params = current_params.copy()

        # Добавляем текущие параметры в историю для prev()
        full_history = history + [current_params]

        # Создаём контекст для вычислений
        context = self._create_calculation_context(new_params, full_history)

        # Применяем формулы в заданном порядке
        calc_order = self.get_calculation_order()

        for calc_group in calc_order:
            if calc_group in self._formulas:
                formulas = self._formulas[calc_group]
                if isinstance(formulas, dict):
                    for param_name, formula in formulas.items():
                        if isinstance(formula, str):
                            try:
                                value = self._evaluate_formula(
                                    formula, new_params, full_history
                                )
                                new_params[param_name] = self._round_value(
                                    value, param_name
                                )
                                # Обновляем контекст
                                context[param_name] = new_params[param_name]
                            except Exception as e:
                                logger.warning(
                                    "Ошибка расчёта %s в группе %s: %s",
                                    param_name, calc_group, e,
                                    exc_info=True,
                                )

        if recalculate_decisions:
            self.apply_decision_formulas(new_params, full_history)

        # Зажимаем отрицательные значения в 0
        for key in new_params:
            if new_params[key] < 0:
                new_params[key] = 0.0

        # Применяем специальные правила
        self._apply_special_rules(new_params, full_history)

        return new_params

    def get_decision_parameter_names(self) -> list[str]:
        decisions = self._formulas.get("decisions", {})
        if not isinstance(decisions, dict):
            return []
        return [
            param_name
            for param_name, formula in decisions.items()
            if isinstance(formula, str)
        ]

    def apply_decision_formulas(
        self,
        params: dict[str, float],
        history: list[dict[str, float]],
    ) -> dict[str, float]:
        decisions = self._formulas.get("decisions", {})
        if not isinstance(decisions, dict):
            return params

        for param_name, formula in decisions.items():
            if isinstance(formula, str):
                try:
                    value = self._evaluate_formula(formula, params, history)
                    params[param_name] = self._round_value(value, param_name)
                except Exception as e:
                    logger.warning(
                        "Ошибка расчёта %s в decisions: %s",
                        param_name,
                        e,
                        exc_info=True,
                    )

        return params

    def apply_decision(
        self,
        params: dict[str, float],
        param_name: str,
        value: float,
        history: list[dict[str, float]],
    ) -> dict[str, float]:
        """
        Применяет решение игрока и пересчитывает зависимые параметры.

        Args:
            params: Текущие параметры
            param_name: Имя параметра для установки
            value: Значение параметра
            history: История параметров

        Returns:
            Обновлённые параметры
        """
        # Устанавливаем значение
        params[param_name] = value

        # Находим и применяем автоматические расчёты
        if "decisions" in self._formulas:
            decisions = self._formulas["decisions"]
            if isinstance(decisions, dict):
                for dep_param, formula in decisions.items():
                    if isinstance(formula, str) and param_name in formula:
                        try:
                            new_value = self._evaluate_formula(formula, params, history)
                            params[dep_param] = self._round_value(new_value, dep_param)
                        except Exception:
                            pass

        return params

    def validate_input(
        self,
        params: dict[str, float],
        param_name: str,
        value: float,
        history: list[dict[str, float]],
    ) -> tuple[bool, Optional[str], Optional[tuple[float, float]]]:
        """
        Проверяет корректность вводимого значения.

        Args:
            params: Текущие параметры
            param_name: Имя параметра
            value: Проверяемое значение
            history: История параметров

        Returns:
            Кортеж (is_valid, error_message, (min, max))
        """
        config = self._parameters_config.get(param_name)
        if not config:
            return True, None, None

        if not config.get("is_input", False):
            return False, f"Параметр {param_name} не является вводимым", None

        # Вычисляем границы
        min_val = self._get_bound(config.get("min", 0), params, history)
        max_val = self._get_bound(config.get("max"), params, history)
        if min_val is not None:
            min_val = self._round_value(min_val, param_name)
        if max_val is not None:
            max_val = self._round_value(max_val, param_name)

        bounds = (min_val, max_val if max_val is not None else float("inf"))

        if min_val is not None and value < min_val:
            return (
                False,
                f"Значение {value} меньше минимума {min_val}",
                bounds,
            )

        if max_val is not None and value > max_val:
            return (
                False,
                f"Значение {value} больше максимума {max_val}",
                bounds,
            )

        return True, None, bounds

    def get_parameter_bounds(
        self,
        params: dict[str, float],
        param_name: str,
        history: list[dict[str, float]],
    ) -> tuple[Optional[float], Optional[float]]:
        """
        Возвращает текущие границы для параметра.

        Args:
            params: Текущие параметры
            param_name: Имя параметра
            history: История параметров

        Returns:
            Кортеж (min, max)
        """
        config = self._parameters_config.get(param_name)
        if not config:
            return None, None

        min_val = self._get_bound(config.get("min", 0), params, history)
        max_val = self._get_bound(config.get("max"), params, history)
        if min_val is not None:
            min_val = self._round_value(min_val, param_name)
        if max_val is not None:
            max_val = self._round_value(max_val, param_name)

        return min_val, max_val

    def is_fixed_parameter(self, param_name: str) -> bool:
        """
        Проверяет, является ли параметр фиксированным (min и max формулы одинаковы).

        Фиксированный параметр - это параметр, где в конфигурации min и max
        заданы одинаковыми выражениями (например, min: "P11 / 5", max: "P11 / 5").

        Args:
            param_name: Имя параметра

        Returns:
            True если параметр фиксированный, False иначе
        """
        config = self._parameters_config.get(param_name)
        if not config or not isinstance(config, dict):
            return False

        min_expr = config.get("min")
        max_expr = config.get("max")

        # Оба должны быть заданы
        if min_expr is None or max_expr is None:
            return False

        # Преобразуем к строкам для сравнения
        min_str = str(min_expr).strip()
        max_str = str(max_expr).strip()

        return min_str == max_str

    def _get_bound(
        self,
        bound_expr: Any,
        params: dict[str, float],
        history: list[dict[str, float]],
    ) -> Optional[float]:
        """Вычисляет значение границы."""
        if bound_expr is None:
            return None

        if isinstance(bound_expr, (int, float)):
            return float(bound_expr)

        if isinstance(bound_expr, str):
            try:
                return self._evaluate_formula(bound_expr, params, history)
            except Exception:
                return None

        return None

    def _create_evaluator(self) -> SimpleEval:
        """Создаёт безопасный вычислитель формул."""
        evaluator = SimpleEval()
        evaluator.functions = {
            "min": min,
            "max": max,
            "round": round,
            "abs": abs,
            "float": float,
            "int": int,
        }
        return evaluator

    def _evaluate_formula(
        self,
        formula: str,
        params: dict[str, float],
        history: list[dict[str, float]],
    ) -> float:
        """
        Вычисляет значение формулы.

        Args:
            formula: Строка формулы
            params: Текущие параметры
            history: История параметров

        Returns:
            Вычисленное значение
        """
        # Создаём контекст для вычисления
        context = self._create_calculation_context(params, history)

        # Заменяем специальные функции
        processed = self._process_formula(formula, params, history)

        # Вычисляем через безопасный evaluator
        evaluator = self._create_evaluator()
        # Переносим callable-объекты из context в functions
        for key in list(context.keys()):
            if callable(context[key]):
                evaluator.functions[key] = context.pop(key)
        evaluator.names = context
        try:
            result = evaluator.eval(processed)
            return float(result) if result is not None else 0.0
        except ZeroDivisionError:
            return 0.0
        except Exception as e:
            raise ValueError(f"Ошибка вычисления формулы '{formula}': {e}")

    def _process_formula(
        self,
        formula: str,
        params: dict[str, float],
        history: list[dict[str, float]],
    ) -> str:
        """
        Обрабатывает формулу, заменяя специальные функции.

        Заменяет:
        - interpolate(TABLE, expr) -> _interpolate_TABLE(expr)
        - prev(PARAM) -> _prev_PARAM
        - mean(PARAM, N) -> _mean_PARAM_N
        """
        processed = formula

        # Заменяем interpolate(TABLE, expr)
        def replace_interpolate(match):
            table = match.group(1)
            expr = match.group(2)
            return f"_interpolate('{table}', {expr})"

        processed = re.sub(
            r"interpolate\s*\(\s*([A-Z][A-Z0-9]*)\s*,\s*(.+?)\s*\)",
            replace_interpolate,
            processed,
        )

        # Заменяем prev(PARAM) на значение из предыдущего периода
        def replace_prev(match):
            param = match.group(1)
            return f"_prev('{param}')"

        processed = re.sub(
            r"prev\s*\(\s*([A-Z][A-Z0-9]*)\s*\)",
            replace_prev,
            processed,
        )

        # Заменяем mean(PARAM, N)
        def replace_mean(match):
            param = match.group(1)
            periods = match.group(2)
            return f"_mean('{param}', {periods})"

        processed = re.sub(
            r"mean\s*\(\s*([A-Z][A-Z0-9]*)\s*,\s*(\d+)\s*\)",
            replace_mean,
            processed,
        )

        return processed

    def _create_calculation_context(
        self,
        params: dict[str, float],
        history: list[dict[str, float]],
    ) -> dict[str, Any]:
        """
        Создаёт контекст для вычисления формул.

        Returns:
            Словарь с переменными и функциями для eval
        """
        context = {}

        # Добавляем все параметры
        context.update(params)

        # Добавляем базовые функции
        context["min"] = min
        context["max"] = max
        context["abs"] = abs
        context["round"] = round

        # Функция интерполяции
        def _interpolate(table: str, value: float) -> float:
            return self._interpolator.interpolate(table, value)

        context["_interpolate"] = _interpolate

        # Функция получения предыдущего значения
        def _prev(param: str) -> float:
            if history:
                prev_period = history[-1]
                return prev_period.get(param, 0.0)
            return params.get(param, 0.0)

        context["_prev"] = _prev

        # Функция среднего
        def _mean(param: str, periods: int) -> float:
            if not history:
                return params.get(param, 0.0)

            values = []
            for i in range(min(periods, len(history))):
                period = history[-(i + 1)]
                values.append(period.get(param, 0.0))

            if not values:
                return params.get(param, 0.0)

            return mean(values) if values else 0.0

        context["_mean"] = _mean

        profile_meta = self._get_profile_metadata(params, history)

        def _energy_output(capital: float) -> float:
            curve = str(profile_meta.get("energy_curve", "LOW")).upper()
            table_name = {
                "HIGH": "E1_HIGH",
                "LOW": "E1_LOW",
            }.get(curve, "E1")
            return self._interpolator.interpolate(table_name, capital)

        def _max_loan() -> float:
            avg_export = _mean("TF10", 3) + _mean("TF11", 3) + _mean("TF12", 3)
            return avg_export if params.get("TF1", 0.0) < avg_export else 0.0

        def _oil_crisis_multiplier() -> float:
            start_cycle = profile_meta.get("oil_crisis_year")
            duration = int(profile_meta.get("oil_crisis_duration", 2) or 2)
            if not isinstance(start_cycle, int):
                return 1.0

            calculated_period_number = len(history) + 1
            if start_cycle <= calculated_period_number < start_cycle + duration:
                return 2.0
            return 1.0

        def _import_energy_price(base_multiplier: float) -> float:
            return base_multiplier * _oil_crisis_multiplier()

        context["energy_output"] = _energy_output
        context["max_loan"] = _max_loan
        context["oil_crisis_multiplier"] = _oil_crisis_multiplier
        context["import_energy_price"] = _import_energy_price

        return context

    def _resolve_profile_config(
        self,
        difficulty: str,
        visited: Optional[set[str]] = None,
    ) -> dict[str, Any]:
        """Разрешает профиль сложности вместе со служебной metadata."""
        if difficulty in self._resolved_profile_configs:
            return dict(self._resolved_profile_configs[difficulty])

        if visited is None:
            visited = set()

        profile = self._initial_profiles.get(difficulty)
        if profile is None and difficulty != "standard":
            profile = self._initial_profiles.get("standard", {})
        if not isinstance(profile, dict):
            return {"meta": {}, "overrides": {}}

        if difficulty in visited:
            raise ValueError(f"Циклическое наследование профиля сложности: {difficulty}")

        visited = visited | {difficulty}
        resolved_meta: dict[str, Any] = {}
        resolved_overrides: dict[str, Any] = {}

        parent = profile.get("extends")
        if isinstance(parent, str) and parent:
            parent_config = self._resolve_profile_config(parent, visited)
            resolved_meta.update(parent_config.get("meta", {}))
            resolved_overrides.update(parent_config.get("overrides", {}))

        meta = profile.get("meta", {})
        if isinstance(meta, dict):
            resolved_meta.update(meta)

        overrides = profile.get("overrides", {})
        if isinstance(overrides, dict):
            resolved_overrides.update(overrides)

        resolved = {"meta": resolved_meta, "overrides": resolved_overrides}
        self._resolved_profile_configs[difficulty] = resolved
        return dict(resolved)

    def _detect_profile_name(
        self,
        params: dict[str, float],
        history: list[dict[str, float]],
    ) -> str:
        """Определяет профиль сложности по начальному снимку параметров."""
        anchor = history[0] if history else params
        matched_name = "standard"
        matched_keys = -1

        for name in self._initial_profiles.keys():
            resolved = self._resolve_profile_config(name)
            overrides = resolved.get("overrides", {})
            comparable = {
                key: value
                for key, value in overrides.items()
                if key in anchor and isinstance(value, (int, float))
            }
            if not comparable:
                continue

            if all(
                abs(anchor.get(key, 0.0) - value) < 1e-9
                for key, value in comparable.items()
            ) and len(comparable) > matched_keys:
                matched_name = name
                matched_keys = len(comparable)

        return matched_name

    def _get_profile_metadata(
        self,
        params: dict[str, float],
        history: list[dict[str, float]],
    ) -> dict[str, Any]:
        """Возвращает metadata активного профиля сложности."""
        profile_name = self._detect_profile_name(params, history)
        return self._resolve_profile_config(profile_name).get("meta", {})

    def _substitute_formula(
        self,
        formula: str,
        params: dict[str, float],
        history: list[dict[str, float]],
    ) -> str:
        """
        Подставляет числовые значения в формулу для наглядного отображения.

        Заменяет:
        - prev(PARAM) → числовое значение из предыдущего периода
        - mean(PARAM, N) → вычисленное среднее
        - interpolate(TABLE, expr) → interpolate(TABLE, <число>)
        - Имена параметров → их текущие значения
        """
        result = formula

        # Заменяем prev(PARAM) на значение
        def replace_prev(match):
            param = match.group(1)
            if history:
                val = history[-1].get(param, 0.0)
            else:
                val = params.get(param, 0.0)
            return self._format_number(val)

        result = re.sub(
            r"prev\s*\(\s*([A-Z][A-Z0-9]*)\s*\)",
            replace_prev,
            result,
        )

        # Заменяем mean(PARAM, N) на вычисленное значение
        def replace_mean(match):
            param = match.group(1)
            periods = int(match.group(2))
            if not history:
                val = params.get(param, 0.0)
            else:
                values = []
                for i in range(min(periods, len(history))):
                    period = history[-(i + 1)]
                    values.append(period.get(param, 0.0))
                val = mean(values) if values else params.get(param, 0.0)
            return self._format_number(val)

        result = re.sub(
            r"mean\s*\(\s*([A-Z][A-Z0-9]*)\s*,\s*(\d+)\s*\)",
            replace_mean,
            result,
        )

        # Заменяем выражение внутри interpolate на числовое значение
        def replace_interpolate(match):
            table = match.group(1)
            expr = match.group(2)
            try:
                # Вычисляем выражение-аргумент
                context = self._create_calculation_context(params, history)
                processed = self._process_formula(expr, params, history)
                val = eval(processed, {"__builtins__": {}}, context)
                return f"interpolate({table}, {self._format_number(val)})"
            except Exception:
                return match.group(0)

        result = re.sub(
            r"interpolate\s*\(\s*([A-Z][A-Z0-9]*)\s*,\s*(.+?)\s*\)",
            replace_interpolate,
            result,
        )

        # Заменяем имена параметров на значения
        def replace_param(match):
            param = match.group(0)
            if param in params:
                return self._format_number(params[param])
            return param

        result = re.sub(r"\b([A-Z][A-Z0-9]*)\b", replace_param, result)

        return result

    @staticmethod
    def _format_number(val: float) -> str:
        """Форматирует число для отображения в подстановке."""
        if val == int(val):
            return str(int(val))
        return f"{val:.2f}"

    def evaluate_with_substitution(
        self,
        formula: str,
        params: dict[str, float],
        history: list[dict[str, float]],
    ) -> dict:
        """
        Вычисляет формулу и возвращает пошаговую подстановку.

        Returns:
            {
                "formula": "prev(P1) + prev(P1)/1000 * (P8-P5) * 5",
                "substituted": "200 + 200/1000 * (41-18) * 5",
                "result": 223.0
            }
        """
        context = self._create_calculation_context(params, history)
        processed = self._process_formula(formula, params, history)

        # Подставляем значения параметров в формулу для отображения
        substituted = formula

        # Заменяем prev(PARAM) на значение
        def replace_prev_display(match):
            param = match.group(1)
            if history:
                val = history[-1].get(param, 0.0)
            else:
                val = params.get(param, 0.0)
            return str(round(val, 2))

        substituted = re.sub(
            r"prev\s*\(\s*([A-Z][A-Z0-9]*)\s*\)",
            replace_prev_display,
            substituted,
        )

        # Заменяем имена параметров на значения (но не функции)
        for name in sorted(params.keys(), key=len, reverse=True):
            if re.search(rf'\b{name}\b', substituted):
                substituted = re.sub(
                    rf'\b{name}\b',
                    str(round(params.get(name, 0), 2)),
                    substituted,
                )

        # Вычисляем результат
        try:
            evaluator = self._create_evaluator()
            ctx = dict(context)
            for key in list(ctx.keys()):
                if callable(ctx[key]):
                    evaluator.functions[key] = ctx.pop(key)
            evaluator.names = ctx
            result = float(evaluator.eval(processed))
        except Exception:
            result = 0.0

        return {
            "formula": formula,
            "substituted": substituted,
            "result": round(result, 2),
        }

    def get_all_formulas_with_substitutions(
        self,
        params: dict[str, float],
        history: list[dict[str, float]],
    ) -> dict[str, dict]:
        """Возвращает формулы с подстановками для всех параметров."""
        result = {}

        # Формулы из calc_* групп
        for group_name in self.get_calculation_order():
            formulas = self._formulas.get(group_name, {})
            if isinstance(formulas, dict):
                for param_name, formula in formulas.items():
                    if isinstance(formula, str):
                        result[param_name] = self.evaluate_with_substitution(
                            formula, params, history
                        )

        # Формулы из decisions (применяются при вводе решений, не при расчёте периода)
        decisions = self._formulas.get("decisions", {})
        if isinstance(decisions, dict):
            for param_name, formula in decisions.items():
                if isinstance(formula, str):
                    entry = self.evaluate_with_substitution(
                        formula, params, history
                    )
                    entry["is_decision"] = True
                    result[param_name] = entry

        return result

    def get_calculations_detail(
        self,
        current_params: dict[str, float],
        history: list[dict[str, float]],
    ) -> list[dict[str, Any]]:
        """
        Возвращает детальную информацию о расчётах текущего периода.

        Для каждой группы формул возвращает параметры с:
        - name: код параметра
        - verbose_name: описание
        - formula: исходная формула
        - substituted: формула с подставленными значениями
        - result: итоговое значение
        """
        group_names = {
            "calc_energy": "Энергетика",
            "calc_agriculture": "Сельское хозяйство",
            "calc_industry": "Промышленность",
            "calc_finance": "Финансы",
            "calc_population": "Население",
            "calc_capital": "Капитал",
            "calc_energy_consumption": "Энергопотребление",
            "calc_production_indicators": "Производственные показатели",
            "calc_trade_finance": "Торговля и финансы",
            "calc_energy_balance": "Энергетический баланс",
            "calc_goods_production": "Производство товаров",
            "calc_food_production": "Производство продовольствия",
            "calc_final_totals": "Итоговые балансы",
            "decisions": "Решения (авто-расчёт)",
        }

        result = []
        calc_order = self.get_calculation_order()

        # Добавляем decisions в конец
        groups_to_process = calc_order + ["decisions"]

        for group_key in groups_to_process:
            if group_key not in self._formulas:
                continue
            formulas = self._formulas[group_key]
            if not isinstance(formulas, dict):
                continue

            parameters = []
            for param_name, formula in formulas.items():
                if not isinstance(formula, str):
                    continue

                config = self._parameters_config.get(param_name, {})
                verbose_name = (
                    config.get("verbose_name", param_name)
                    if isinstance(config, dict)
                    else param_name
                )

                substituted = self._substitute_formula(formula, current_params, history)
                value = current_params.get(param_name, 0)

                parameters.append(
                    {
                        "name": param_name,
                        "verbose_name": verbose_name,
                        "formula": formula,
                        "substituted": substituted,
                        "result": value,
                    }
                )

            if parameters:
                result.append(
                    {
                        "group": group_key,
                        "group_name": group_names.get(group_key, group_key),
                        "parameters": parameters,
                    }
                )

        return result

    def _round_value(self, value: float, param_name: str) -> float:
        """
        Округляет значение в зависимости от параметра.

        Применяет правила округления из legacy кода:
        - Население и некоторые показатели округляются до десятков
        - Проценты округляются до 1-2 знаков
        - Остальные - до целых
        """
        if value is None:
            return 0.0

        # Параметры с двумя знаками после запятой
        decimal_2_params = {
            "P4",
            "P6",
            "P7",
            "E8",
            "E10",
            "F7",
            "F8",
            "F10",
            "G7",
            "G8",
            "G9",
            "G10",
            "G11",
            "TF2",
            "TF3",
            "TF4",
            "TF6",
            "TF7",
            "TF8",
        }

        # Параметры с одним знаком после запятой в Excel-листах.
        decimal_1_params = {
            "E11",
            "E16",
        }

        # Параметры, для которых в документации явно указано округление до десятков.
        round_10_params = {"P1", "E9", "E20"}

        if param_name in round_10_params:
            return self._round_half_up(value, -1)
        if param_name in decimal_1_params:
            return self._round_half_up(value, 1)
        if param_name in decimal_2_params:
            return self._round_half_up(value, 2)
        return self._round_half_up(value, 0)

    @staticmethod
    def _round_half_up(value: float, decimals: int) -> float:
        """Округление как в Excel/BASIC: .5 всегда вверх, без bankers rounding."""
        quantum = Decimal("1").scaleb(-decimals)
        return float(Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP))

    def _apply_special_rules(
        self,
        params: dict[str, float],
        history: list[dict[str, float]],
    ) -> None:
        """
        Применяет специальные правила расчётов.

        Например, штраф при высоком долге.
        """
        # Штраф при высоком долге
        tf1 = params.get("TF1", 0)
        p2 = params.get("P2", 0)
        p3 = params.get("P3", 0)

        e7 = params.get("E7", 0)

        if tf1 > 0.5 * (p3 + p2 + e7):
            seized_goods = p3 * 0.1
            params["P3"] = self._round_value(max(p3 - seized_goods, 0.0), "P3")

    def get_default_parameters(self) -> dict[str, float]:
        """Возвращает параметры по умолчанию для начала игры."""
        defaults = {}
        for param_name, config in self._parameters_config.items():
            if isinstance(config, dict):
                defaults[param_name] = config.get("default", 0)
            else:
                defaults[param_name] = config
        return defaults

    def get_initial_parameters(self, difficulty: str = "standard") -> dict[str, float]:
        """Возвращает стартовые параметры для выбранной сложности."""
        defaults = self.get_default_parameters()
        profile = self._resolve_initial_profile(difficulty)

        for param_name, value in profile.items():
            if param_name in self._parameters_config:
                defaults[param_name] = value

        return defaults

    def _resolve_initial_profile(
        self,
        difficulty: str,
        visited: Optional[set[str]] = None,
    ) -> dict[str, float]:
        """Разрешает профиль сложности с поддержкой extends."""
        return self._resolve_profile_config(difficulty, visited).get("overrides", {})

    def get_input_parameters(self) -> list[str]:
        """Возвращает список вводимых параметров."""
        inputs = []
        for param_name, config in self._parameters_config.items():
            if isinstance(config, dict) and config.get("is_input", False):
                inputs.append(param_name)
        return inputs

    def get_parameters_config(self) -> dict:
        """Возвращает конфигурацию параметров."""
        return dict(self._parameters_config)

    def get_interpolation_tables(self) -> dict:
        """Возвращает все таблицы интерполяции для отображения."""
        return self._interpolator.get_all_tables()


# Глобальный экземпляр калькулятора
_calculator: Optional[GameCalculator] = None


def get_calculator() -> GameCalculator:
    """Возвращает глобальный экземпляр калькулятора."""
    global _calculator
    if _calculator is None:
        _calculator = GameCalculator()
    return _calculator
