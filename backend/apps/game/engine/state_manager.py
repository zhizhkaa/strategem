"""
Менеджер состояния игры Стратегема.

Управляет состоянием игры, отслеживает прогресс принятия решений
и предоставляет полную информацию о текущем состоянии для UI и агентов.
"""

from pathlib import Path
from typing import Any

import yaml

from .calculator import GameCalculator, get_calculator


class DecisionState:
    """Состояние принятия решений в текущем периоде."""

    def __init__(self):
        """Инициализация состояний решений."""
        self.reset()

    def reset(self) -> None:
        """Сброс всех состояний решений."""
        self.states = {
            "capital": 0,  # Уровень принятия решений по капиталовложениям (0-4)
            "energy": 0,  # Уровень принятия решений по энергетике (0-1)
            "finance": 0,  # Уровень принятия финансовых решений (0-3)
            "import": 0,  # Уровень принятия решений по импорту (0-3)
        }

    def check(self, category: str, required_level: int) -> bool:
        """
        Проверяет, достигнут ли требуемый уровень решений.

        Args:
            category: Категория решений (capital, energy, finance, import)
            required_level: Требуемый уровень

        Returns:
            True если уровень достигнут или превышен
        """
        return self.states.get(category, 0) >= required_level

    def set(self, category: str, level: int) -> bool:
        """
        Устанавливает уровень решений.

        Уровень устанавливается только если новое значение выше текущего,
        чтобы повторная отправка параметров не понижала уже достигнутый уровень.

        Args:
            category: Категория решений
            level: Новый уровень

        Returns:
            True если установка успешна
        """
        if category in self.states:
            if level > self.states[category]:
                self.states[category] = level
            return True
        return False

    def to_dict(self) -> dict[str, int]:
        """Возвращает состояния как словарь."""
        return self.states.copy()

    def from_dict(self, data: dict[str, int]) -> None:
        """Загружает состояния из словаря."""
        for key in self.states:
            if key in data:
                self.states[key] = data[key]


class GameStateManager:
    """
    Менеджер состояния игры.

    Отвечает за:
    - Отслеживание текущего состояния всех параметров
    - Управление прогрессом принятия решений
    - Валидацию вводимых значений
    - Генерацию полного отчёта о состоянии игры
    """

    def __init__(self, calculator: GameCalculator | None = None):
        """
        Инициализация менеджера состояния.

        Args:
            calculator: Калькулятор игры (или используется глобальный)
        """
        self._calculator = calculator or get_calculator()
        self._decision_order: dict = {}
        self._parameters_config: dict = {}
        self._load_config()

    def _load_config(self) -> None:
        """Загружает конфигурацию из YAML-файлов."""
        data_dir = Path(__file__).parent.parent / "data"

        # Загружаем порядок решений
        order_path = data_dir / "decision_order.yaml"
        if order_path.exists():
            with open(order_path, "r", encoding="utf-8") as f:
                self._decision_order = yaml.safe_load(f) or {}

        # Читаем флаг параллельного режима
        self.parallel_mode: bool = bool(self._decision_order.get("parallel_mode", False))

        # Загружаем конфигурацию параметров
        params_path = data_dir / "parameters.yaml"
        if params_path.exists():
            with open(params_path, "r", encoding="utf-8") as f:
                params_data = yaml.safe_load(f) or {}
                for category_name, category in params_data.items():
                    if isinstance(category, dict):
                        for param_name, param_config in category.items():
                            if isinstance(param_config, dict):
                                param_config["category"] = category_name
                            self._parameters_config[param_name] = param_config

    def _iter_decision_stages(self):
        """Итерирует только по этапам решений из decision_order."""
        for stage_key, stage_config in self._decision_order.items():
            if isinstance(stage_config, dict) and "order" in stage_config:
                yield stage_key, stage_config

    def _is_team_stage(self, stage_config: dict[str, Any]) -> bool:
        """Возвращает True для этапов стандартного командного flow."""
        return stage_config.get("flow", "team") == "team"

    def _get_stage_inputs(
        self,
        stage_config: dict[str, Any],
        *,
        include_operator_controlled: bool = False,
    ) -> list[dict[str, Any]]:
        """Возвращает inputs этапа, при необходимости исключая operator-controlled."""
        result = []
        for inp in stage_config.get("inputs", []):
            if not isinstance(inp, dict):
                continue
            if (
                not include_operator_controlled
                and inp.get("controller", "team") != "team"
            ):
                continue
            result.append(inp)
        return result

    def _get_stage_for_param(self, param_name: str) -> tuple[str | None, dict | None]:
        """Находит этап, к которому относится параметр."""
        for stage_key, stage_config in self._iter_decision_stages():
            inputs = self._get_stage_inputs(
                stage_config, include_operator_controlled=True
            )
            if any(inp.get("param") == param_name for inp in inputs):
                return stage_key, stage_config
        return None, None

    def get_batch_processing_order(
        self, param_names: list[str] | set[str] | tuple[str, ...]
    ) -> list[str]:
        """Сортирует параметры в порядке этапов и полей внутри этапа."""
        indexed_params: list[tuple[int, int, int, str]] = []

        for fallback_index, param_name in enumerate(param_names):
            _stage_key, stage_config = self._get_stage_for_param(param_name)
            if stage_config is None:
                indexed_params.append((999, 999, fallback_index, param_name))
                continue

            inputs = self._get_stage_inputs(
                stage_config, include_operator_controlled=True
            )
            input_index = next(
                (
                    idx
                    for idx, inp in enumerate(inputs)
                    if inp.get("param") == param_name
                ),
                999,
            )
            indexed_params.append(
                (stage_config.get("order", 999), input_index, fallback_index, param_name)
            )

        indexed_params.sort()
        return [param_name for _, _, _, param_name in indexed_params]

    def is_operator_controlled_param(self, param_name: str) -> bool:
        """Проверяет, помечен ли параметр как operator-controlled."""
        _stage_key, stage_config = self._get_stage_for_param(param_name)
        if stage_config is None:
            return False

        for inp in self._get_stage_inputs(stage_config, include_operator_controlled=True):
            if inp.get("param") == param_name:
                return inp.get("controller", "team") != "team"

        return False

    def get_operator_controlled_params(self) -> set[str]:
        """Возвращает множество operator-controlled input-параметров."""
        result = set()
        for _stage_key, stage_config in self._iter_decision_stages():
            for inp in self._get_stage_inputs(
                stage_config, include_operator_controlled=True
            ):
                if inp.get("controller", "team") != "team" and inp.get("param"):
                    result.add(inp["param"])
        return result

    def get_full_state(
        self,
        params: dict[str, float],
        decision_state: DecisionState,
        history: list[dict[str, float]],
        current_period: int,
        total_periods: int,
        user_inputs: list[str] = None,
    ) -> dict[str, Any]:
        """
        Возвращает полное состояние игры.

        Используется для отрисовки UI и для ИИ-агентов.

        Args:
            params: Текущие параметры
            decision_state: Состояние решений
            history: История параметров
            current_period: Текущий период
            total_periods: Всего периодов
            user_inputs: Список параметров, явно введённых пользователем

        Returns:
            Полное состояние игры со всей необходимой информацией
        """
        # Сохраняем текущие параметры для использования в других методах
        self._current_params = params

        # Определяем статус каждого параметра
        parameters_state = self._get_parameters_state(
            params, decision_state, history, user_inputs
        )

        # Определяем доступные этапы решений
        available_stages = self._get_available_stages(
            decision_state, params, user_inputs
        )

        # Определяем следующие действия
        next_actions = self._get_next_actions(decision_state, user_inputs)

        # Проверяем, можно ли перейти к следующему периоду
        can_advance = self._can_advance_period(decision_state, user_inputs)

        return {
            "game_info": {
                "current_period": current_period,
                "total_periods": total_periods,
                "can_advance_period": can_advance,
            },
            "decision_states": decision_state.to_dict(),
            "parameters": parameters_state,
            "available_stages": available_stages,
            "next_actions": next_actions,
            "ministers": self._get_ministers_info(),
        }

    def _get_parameters_state(
        self,
        params: dict[str, float],
        decision_state: DecisionState,
        history: list[dict[str, float]],
        user_inputs: list[str] = None,
    ) -> dict[str, dict[str, Any]]:
        """
        Возвращает состояние всех параметров с метаданными.

        Для каждого параметра возвращает:
        - value: текущее значение
        - verbose_name: человекочитаемое название
        - category: категория параметра
        - is_input: является ли вводимым
        - status: filled / empty / next_to_fill / locked
        - bounds: (min, max) если применимо
        - depends_on: от каких параметров зависит

        Args:
            params: Текущие параметры
            decision_state: Состояние решений
            history: История параметров
            user_inputs: Список параметров, явно введённых пользователем
        """
        if user_inputs is None:
            user_inputs = []
        result = {}

        # Определяем, какие параметры сейчас можно заполнять
        fillable_params = self._get_fillable_params(decision_state)

        for param_name, config in self._parameters_config.items():
            if not isinstance(config, dict):
                config = {"default": config}

            value = params.get(param_name, config.get("default", 0))
            is_input = config.get("is_input", False)

            # Получаем границы для вводимых параметров
            bounds = None
            is_truly_fixed = False
            if is_input:
                min_val, max_val = self._calculator.get_parameter_bounds(
                    params, param_name, history
                )
                bounds = {
                    "min": min_val,
                    "max": max_val,
                }
                # Проверяем, является ли параметр действительно фиксированным
                # (min и max выражения идентичны в конфигурации)
                is_truly_fixed = self._calculator.is_fixed_parameter(param_name)

            # Определяем статус
            if is_input:
                # Параметр считается заполненным если:
                # 1. Параметр был явно введён пользователем (есть в user_inputs), ИЛИ
                # 2. Параметр действительно фиксированный (min формула == max формула)
                #    и значение равно этому фиксированному значению, ИЛИ
                # 3. Значение отличается от 0 и default (для обратной совместимости)
                if param_name in user_inputs:
                    status = "filled"
                elif is_truly_fixed and bounds and value == bounds["min"]:
                    status = "filled"
                elif value != 0 and value != config.get("default", 0):
                    status = "filled"
                elif param_name in fillable_params:
                    status = "next_to_fill"
                else:
                    status = "locked"
            else:
                status = "calculated"

            result[param_name] = {
                "value": value,
                "verbose_name": config.get("verbose_name", param_name),
                "category": config.get("category", "unknown"),
                "is_input": is_input,
                "status": status,
                "bounds": bounds,
                "is_fixed": is_truly_fixed,
                "depends_on": config.get("depends_on", []),
                "decision_group": config.get("decision_group"),
            }

        return result

    def _get_fillable_params(self, decision_state: DecisionState) -> set[str]:
        """
        Определяет, какие параметры можно заполнять в текущем состоянии.

        Returns:
            Множество имён параметров, доступных для ввода
        """
        fillable = set()

        for _stage_key, stage_config in self._iter_decision_stages():
            if not self._is_team_stage(stage_config):
                continue

            # Проверяем требования этапа
            requirements = stage_config.get("requires", [])
            requirements_met = True

            for req in requirements:
                if isinstance(req, dict):
                    category = req.get("category")
                    level = req.get("level", 0)
                    if not decision_state.check(category, level):
                        requirements_met = False
                        break

            if not requirements_met:
                continue

            # Проверяем, не завершён ли уже этот этап
            sets_decision = stage_config.get("sets_decision")
            if sets_decision:
                if isinstance(sets_decision, dict):
                    if decision_state.check(
                        sets_decision.get("category", ""),
                        sets_decision.get("level", 0),
                    ):
                        continue
                elif isinstance(sets_decision, list):
                    all_set = True
                    for sd in sets_decision:
                        if not decision_state.check(
                            sd.get("category", ""), sd.get("level", 0)
                        ):
                            all_set = False
                            break
                    if all_set:
                        continue

            # Добавляем вводимые параметры этого этапа
            inputs = self._get_stage_inputs(stage_config)
            for inp in inputs:
                fillable.add(inp.get("param", ""))

        return fillable

    def _get_available_stages(
        self,
        decision_state: DecisionState,
        params: dict[str, float] = None,
        user_inputs: list[str] = None,
    ) -> list[dict]:
        """
        Возвращает список доступных этапов решений.

        Args:
            decision_state: Состояние решений
            params: Текущие параметры (для проверки заполненности)
            user_inputs: Список параметров, явно введённых пользователем

        Returns:
            Список этапов с информацией о требованиях и статусе
        """
        if params is None:
            params = getattr(self, "_current_params", {})
        if user_inputs is None:
            user_inputs = []
        stages = []

        for stage_key, stage_config in self._iter_decision_stages():
            if not self._is_team_stage(stage_config):
                continue

            # Проверяем требования этапа
            requirements = stage_config.get("requires", [])
            requirements_met = True
            missing_requirements = []

            for req in requirements:
                if isinstance(req, dict):
                    category = req.get("category")
                    level = req.get("level", 0)
                    if not decision_state.check(category, level):
                        requirements_met = False
                        missing_requirements.append(f"{category} >= {level}")

            # Проверяем, завершён ли этап
            completed = False
            sets_decision = stage_config.get("sets_decision")
            if sets_decision:
                if isinstance(sets_decision, dict):
                    completed = decision_state.check(
                        sets_decision.get("category", ""),
                        sets_decision.get("level", 0),
                    )
                elif isinstance(sets_decision, list) and len(sets_decision) > 0:
                    completed = all(
                        decision_state.check(sd.get("category", ""), sd.get("level", 0))
                        for sd in sets_decision
                    )

            # Для этапов без sets_decision (пустой список или отсутствует)
            # проверяем, все ли input параметры заполнены
            if not sets_decision or (
                isinstance(sets_decision, list) and len(sets_decision) == 0
            ):
                inputs = self._get_stage_inputs(stage_config)
                if inputs and requirements_met:
                    all_inputs_filled = True
                    for inp in inputs:
                        param_name = inp.get("param")
                        if param_name:
                            config = self._parameters_config.get(param_name, {})
                            default = (
                                config.get("default", 0)
                                if isinstance(config, dict)
                                else 0
                            )
                            current_value = params.get(param_name, default)

                            # Проверяем, является ли параметр фиксированным
                            is_fixed = self._calculator.is_fixed_parameter(
                                param_name
                            )

                            if is_fixed:
                                # Для fixed-полей auto-fill считается заполненным
                                # по формуле, а forced snapshot - по факту
                                # явного ввода.
                                min_val, _ = self._calculator.get_parameter_bounds(
                                    params, param_name, []
                                )
                                if (
                                    param_name not in user_inputs
                                    and min_val is not None
                                    and current_value != min_val
                                ):
                                    all_inputs_filled = False
                                    break
                            else:
                                # Для обычных - проверяем, был ли параметр явно введён пользователем
                                # Это позволяет корректно обрабатывать случай, когда
                                # пользователь вводит значение равное default (например, 0)
                                if param_name not in user_inputs:
                                    all_inputs_filled = False
                                    break
                    completed = all_inputs_filled

            stages.append(
                {
                    "key": stage_key,
                    "order": stage_config.get("order", 999),
                    "name": stage_config.get("name", stage_key),
                    "minister": stage_config.get("minister"),
                    "description": stage_config.get("description", ""),
                    "available": requirements_met,
                    "completed": completed,
                    "missing_requirements": missing_requirements,
                    "inputs": [inp.get("param") for inp in self._get_stage_inputs(stage_config)],
                }
            )

        # Сортируем по порядку
        stages.sort(key=lambda x: x["order"])

        return stages

    def _get_next_actions(
        self, decision_state: DecisionState, user_inputs: list[str] = None
    ) -> list[dict]:
        """
        Возвращает список рекомендуемых следующих действий.

        Args:
            decision_state: Состояние решений
            user_inputs: Список параметров, явно введённых пользователем

        Returns:
            Список действий с приоритетом
        """
        actions = []
        stages = self._get_available_stages(decision_state, user_inputs=user_inputs)

        for stage in stages:
            if stage["available"] and not stage["completed"]:
                actions.append(
                    {
                        "stage_key": stage["key"],
                        "name": stage["name"],
                        "minister": stage["minister"],
                        "inputs": stage["inputs"],
                        "priority": stage["order"],
                    }
                )

        # Сортируем по приоритету
        actions.sort(key=lambda x: x["priority"])

        return actions

    def _can_advance_period(
        self, decision_state: DecisionState, user_inputs: list[str] = None
    ) -> bool:
        """
        Проверяет, можно ли перейти к следующему периоду.

        Для перехода необходимо завершить все обязательные этапы.
        В параллельном режиме проверяются все этапы, а не только доступные.
        """
        stages = self._get_available_stages(decision_state, user_inputs=user_inputs)

        for stage in stages:
            if not stage["completed"]:
                return False

        return True

    def get_param_to_minister_map(self) -> dict[str, str]:
        """
        Возвращает словарь {код_параметра: ключ_министра}.

        Строится из ministers-секции decision_order.yaml.
        Используется при валидации для разбивки ошибок по министрам.
        """
        ministers_config = self._decision_order.get("ministers", {})
        param_to_minister: dict[str, str] = {}

        for minister_key, minister_data in ministers_config.items():
            if not isinstance(minister_data, dict):
                continue
            for stage_key in minister_data.get("decisions", []):
                stage_config = self._decision_order.get(stage_key, {})
                if (
                    not isinstance(stage_config, dict)
                    or not self._is_team_stage(stage_config)
                ):
                    continue
                for inp in self._get_stage_inputs(stage_config):
                    if inp.get("param"):
                        param_to_minister[inp["param"]] = minister_key
                for auto in stage_config.get("auto_calculated", []):
                    if isinstance(auto, dict) and auto.get("param"):
                        param_to_minister[auto["param"]] = minister_key

        return param_to_minister

    def get_all_input_params(self) -> list[str]:
        """
        Возвращает список всех вводимых параметров по всем этапам.

        Используется при валидации в параллельном режиме
        для определения всех ожидаемых вводов.
        """
        result = []
        for _stage_key, stage_config in self._iter_decision_stages():
            if not self._is_team_stage(stage_config):
                continue
            for inp in self._get_stage_inputs(stage_config):
                if inp.get("param") and inp["param"] not in result:
                    result.append(inp["param"])
        return result

    def _get_ministers_info(self) -> dict[str, dict]:
        """Возвращает информацию о министрах."""
        ministers_config = self._decision_order.get("ministers", {})
        result = {}

        for minister_key, minister_config in ministers_config.items():
            if isinstance(minister_config, dict):
                result[minister_key] = {
                    "name": minister_config.get("name", minister_key),
                    "decisions": minister_config.get("decisions", []),
                }

        return result

    def set_parameter(
        self,
        params: dict[str, float],
        decision_state: DecisionState,
        param_name: str,
        value: float,
        history: list[dict[str, float]],
        user_inputs: list[str] | None = None,
        force: bool = False,
    ) -> tuple[bool, str | None, dict[str, float]]:
        """
        Устанавливает значение параметра с валидацией.

        Args:
            params: Текущие параметры
            decision_state: Состояние решений
            param_name: Имя параметра
            value: Значение
            history: История
            user_inputs: Список параметров, явно введённых пользователем
            force: Если True — пропустить проверку границ (только для сводного листа)

        Returns:
            Кортеж (success, error_message, updated_params)
        """
        if user_inputs is None:
            user_inputs = []
        # Проверяем, можно ли заполнять этот параметр (пропускается при force=True)
        if not force:
            fillable = self._get_fillable_params(decision_state)
            if param_name not in fillable and param_name not in user_inputs:
                return False, f"Параметр {param_name} сейчас недоступен для ввода", params

        # force=True используется для восстановления/сводного ввода и должен
        # сохранять явно переданное значение, даже если текущая формула дала бы
        # другое fixed/bounds значение.
        if not force:
            is_valid, error, bounds = self._calculator.validate_input(
                params, param_name, value, history
            )
            if not is_valid:
                return False, error, params

        # Применяем значение
        updated_params = self._calculator.apply_decision(
            params.copy(), param_name, value, history
        )

        # Автоматически заполняем фиксированные параметры в том же этапе
        auto_filled_params = []
        if not force:
            updated_params, auto_filled_params = self._auto_fill_fixed_params_in_stage(
                updated_params, param_name, history
            )

        # Обновляем состояние решений
        # Добавляем текущий параметр и автозаполненные к user_inputs для корректной проверки
        updated_user_inputs = list(user_inputs)
        if param_name not in updated_user_inputs:
            updated_user_inputs.append(param_name)
        # Добавляем только автозаполненные фиксированные параметры этого этапа
        for p in auto_filled_params:
            if p not in updated_user_inputs:
                updated_user_inputs.append(p)
        self._update_decision_state(
            decision_state, param_name, updated_params, updated_user_inputs
        )

        return True, None, updated_params

    def _auto_fill_fixed_params_in_stage(
        self,
        params: dict[str, float],
        param_name: str,
        history: list[dict[str, float]],
    ) -> tuple[dict[str, float], list[str]]:
        """
        Автоматически заполняет фиксированные параметры в том же этапе.

        Когда пользователь сохраняет параметр, все фиксированные параметры
        (min == max в конфигурации) того же этапа автоматически заполняются
        своими фиксированными значениями.

        Args:
            params: Текущие параметры
            param_name: Имя только что сохранённого параметра
            history: История

        Returns:
            Кортеж (обновлённые параметры, список автозаполненных параметров)
        """
        filled_params = []

        _stage_key, stage_config = self._get_stage_for_param(param_name)
        if stage_config is None or not self._is_team_stage(stage_config):
            return params, filled_params

        inputs = self._get_stage_inputs(stage_config, include_operator_controlled=True)

        # Нашли этап - теперь заполняем все фиксированные параметры
        for inp in inputs:
            p = inp.get("param")
            if p and self._calculator.is_fixed_parameter(p):
                # Получаем фиксированное значение
                min_val, _ = self._calculator.get_parameter_bounds(
                    params, p, history
                )
                if min_val is not None:
                    params[p] = min_val
                    filled_params.append(p)

        return params, filled_params

    def _update_decision_state(
        self,
        decision_state: DecisionState,
        param_name: str,
        params: dict[str, float],
        user_inputs: list[str] = None,
    ) -> None:
        """
        Обновляет состояние решений после ввода параметра.

        Проверяет, завершён ли текущий этап, и обновляет уровни.

        Args:
            decision_state: Состояние решений
            param_name: Имя параметра, который был введён
            params: Текущие параметры
            user_inputs: Список параметров, явно введённых пользователем
        """
        if user_inputs is None:
            user_inputs = []
        _stage_key, stage_config = self._get_stage_for_param(param_name)
        if stage_config is None or not self._is_team_stage(stage_config):
            return

        inputs = self._get_stage_inputs(stage_config)
        if param_name not in [inp.get("param") for inp in inputs]:
            return

        # Проверяем, все ли параметры этапа заполнены
        all_filled = True
        for inp in inputs:
            p = inp.get("param")
            config = self._parameters_config.get(p, {})
            default = config.get("default", 0) if isinstance(config, dict) else 0
            current_value = params.get(p, default)

            # Получаем границы параметра
            min_val, max_val = self._calculator.get_parameter_bounds(params, p, [])

            # Проверяем, является ли параметр действительно фиксированным
            # (min и max выражения идентичны в конфигурации)
            is_truly_fixed = self._calculator.is_fixed_parameter(p)

            if is_truly_fixed:
                # Для fixed-полей auto-fill считается заполненным по формуле,
                # а forced snapshot - по факту явного ввода.
                if p not in user_inputs and min_val is not None and current_value != min_val:
                    all_filled = False
                    break
            else:
                # Для обычных параметров - проверяем, был ли параметр явно введён пользователем
                # Это позволяет корректно обрабатывать случай, когда
                # пользователь вводит значение равное default (например, 0)
                if p not in user_inputs:
                    all_filled = False
                    break

        if all_filled:
            # Устанавливаем уровни решений
            sets_decision = stage_config.get("sets_decision")
            if sets_decision:
                if isinstance(sets_decision, dict):
                    decision_state.set(
                        sets_decision.get("category", ""),
                        sets_decision.get("level", 0),
                    )
                elif isinstance(sets_decision, list):
                    for sd in sets_decision:
                        decision_state.set(
                            sd.get("category", ""),
                            sd.get("level", 0),
                        )


# Глобальный экземпляр менеджера состояния
_state_manager: GameStateManager | None = None


def get_state_manager() -> GameStateManager:
    """Возвращает глобальный экземпляр менеджера состояния."""
    global _state_manager
    if _state_manager is None:
        _state_manager = GameStateManager()
    return _state_manager
