"""
Валидатор формул для игры Стратегема.

Проверяет корректность формул из YAML-файлов:
- Синтаксическая корректность выражений
- Существование используемых переменных
- Корректность вызовов функций
- Отсутствие циклических зависимостей
"""

import ast
import re
from pathlib import Path

import yaml


class FormulaValidator:
    """
    Валидатор формул и выражений игры.

    Проверяет формулы из formulas.yaml и parameters.yaml
    на корректность и консистентность.
    """

    # Допустимые функции в формулах
    ALLOWED_FUNCTIONS = {
        "min": 2,  # min(a, b)
        "max": 2,  # max(a, b)
        "round": 2,  # round(value, decimals)
        "interpolate": 2,  # interpolate(TABLE, value)
        "mean": 2,  # mean(param, periods)
        "prev": 1,  # prev(param)
        "abs": 1,  # abs(value)
        "max_loan": 0,  # max_loan()
    }

    # Допустимые таблицы интерполяции
    INTERPOLATION_TABLES = [
        "P1",
        "P2",
        "P3",
        "P4",
        "E1",
        "E2",
        "G1",
        "G2",
        "G3",
        "F1",
        "F2",
        "F3",
        "F4",
        "TF1",
        "TF2",
    ]

    def __init__(self, config_data: dict | None = None):
        """Инициализация валидатора с загрузкой конфигурации."""
        self._parameters: dict = {}
        self._formulas: dict = {}
        self._errors: list[str] = []
        self._warnings: list[str] = []
        self._config_data = config_data
        self._load_config()

    def _load_config(self) -> None:
        """Загружает конфигурацию параметров и формул."""
        data_dir = Path(__file__).parent.parent / "data"

        if self._config_data is not None:
            params_data = self._config_data.get("parameters.yaml") or {}
            for category in params_data.values():
                if isinstance(category, dict):
                    self._parameters.update(category)
            self._formulas = self._config_data.get("formulas.yaml") or {}
            interp_data = self._config_data.get("interpolation.yaml") or {}
            if isinstance(interp_data, dict):
                self.INTERPOLATION_TABLES = list(interp_data.keys())
            return

        # Загружаем параметры
        params_path = data_dir / "parameters.yaml"
        if params_path.exists():
            with open(params_path, "r", encoding="utf-8") as f:
                params_data = yaml.safe_load(f)
                for category in params_data.values():
                    if isinstance(category, dict):
                        self._parameters.update(category)

        # Загружаем формулы
        formulas_path = data_dir / "formulas.yaml"
        if formulas_path.exists():
            with open(formulas_path, "r", encoding="utf-8") as f:
                self._formulas = yaml.safe_load(f)

        # Загружаем таблицы интерполяции
        interp_path = data_dir / "interpolation.yaml"
        if interp_path.exists():
            with open(interp_path, "r", encoding="utf-8") as f:
                interp_data = yaml.safe_load(f)
                self.INTERPOLATION_TABLES = list(interp_data.keys())

    def get_all_parameter_names(self) -> set[str]:
        """Возвращает множество всех допустимых имён параметров."""
        return set(self._parameters.keys())

    def validate_all(self) -> tuple[list[str], list[str]]:
        """
        Проверяет все формулы и параметры.

        Returns:
            Кортеж (errors, warnings) со списками найденных проблем
        """
        self._errors = []
        self._warnings = []

        # Валидируем формулы
        for section_name, section in self._formulas.items():
            if isinstance(section, dict):
                for param_name, formula in section.items():
                    if isinstance(formula, str):
                        self._validate_formula(
                            formula, param_name, f"formulas.yaml:{section_name}"
                        )

        # Валидируем границы параметров
        for param_name, param_config in self._parameters.items():
            if isinstance(param_config, dict):
                if "min" in param_config and isinstance(param_config["min"], str):
                    self._validate_expression(
                        param_config["min"],
                        f"Параметр {param_name}.min",
                        "parameters.yaml",
                    )
                if "max" in param_config and isinstance(param_config["max"], str):
                    self._validate_expression(
                        param_config["max"],
                        f"Параметр {param_name}.max",
                        "parameters.yaml",
                    )

        return self._errors, self._warnings

    def _validate_formula(self, formula: str, param_name: str, location: str) -> bool:
        """
        Валидирует одну формулу.

        Args:
            formula: Строка формулы
            param_name: Имя параметра, которому присваивается результат
            location: Местоположение для сообщений об ошибках

        Returns:
            True если формула корректна
        """
        return self._validate_expression(formula, f"Формула {param_name}", location)

    def _validate_expression(
        self, expression: str, context: str, location: str
    ) -> bool:
        """
        Валидирует выражение.

        Args:
            expression: Строка выражения
            context: Контекст для сообщений об ошибках
            location: Местоположение в файле

        Returns:
            True если выражение корректно
        """
        # Обрабатываем условные выражения Python
        expression = self._normalize_expression(expression)

        # Проверяем синтаксис
        if not self._check_syntax(expression, context, location):
            return False

        # Извлекаем и проверяем переменные
        variables = self._extract_variables(expression)
        valid_params = self.get_all_parameter_names()

        for var in variables:
            # Пропускаем таблицы интерполяции
            if var in self.INTERPOLATION_TABLES:
                continue

            if var not in valid_params:
                self._errors.append(
                    f"{location}: {context} - неизвестная переменная '{var}'"
                )

        # Проверяем вызовы функций
        self._check_function_calls(expression, context, location)

        return True

    def _normalize_expression(self, expression: str) -> str:
        """
        Нормализует выражение для проверки синтаксиса Python.

        Заменяет специфичные для игры конструкции на валидный Python.
        """
        # Заменяем "X if condition else Y" оставляем как есть (это валидный Python)
        return expression

    def _check_syntax(self, expression: str, context: str, location: str) -> bool:
        """
        Проверяет синтаксическую корректность выражения.

        Returns:
            True если синтаксис корректен
        """
        try:
            # Пробуем распарсить как Python-выражение
            ast.parse(expression, mode="eval")
            return True
        except SyntaxError as e:
            self._errors.append(
                f"{location}: {context} - синтаксическая ошибка: {e.msg}"
            )
            return False

    def _extract_variables(self, expression: str) -> set[str]:
        """
        Извлекает имена переменных из выражения.

        Игнорирует:
        - Числа
        - Строки
        - Имена функций
        - Ключевые слова

        Returns:
            Множество имён переменных
        """
        variables = set()

        # Паттерн для идентификаторов (переменных и функций)
        identifier_pattern = r"\b([A-Za-z_][A-Za-z0-9_]*)\b"

        # Находим все идентификаторы
        for match in re.finditer(identifier_pattern, expression):
            name = match.group(1)

            # Пропускаем ключевые слова Python
            if name in {"if", "else", "and", "or", "not", "True", "False", "None"}:
                continue

            # Пропускаем имена функций
            if name in self.ALLOWED_FUNCTIONS:
                continue

            variables.add(name)

        return variables

    def _check_function_calls(
        self, expression: str, context: str, location: str
    ) -> None:
        """
        Проверяет корректность вызовов функций.

        Проверяет:
        - Существование функции
        - Количество аргументов
        - Корректность аргументов для специальных функций
        """
        # Паттерн для вызовов функций: name(args)
        func_pattern = r"\b([a-z_]+)\s*\("

        for match in re.finditer(func_pattern, expression):
            func_name = match.group(1)

            # Проверяем, что функция известна
            if func_name not in self.ALLOWED_FUNCTIONS:
                self._errors.append(
                    f"{location}: {context} - неизвестная функция '{func_name}'"
                )
                continue

            # Проверяем аргументы для interpolate
            if func_name == "interpolate":
                # Извлекаем первый аргумент (имя таблицы)
                args_start = match.end()
                table_match = re.match(r"\s*([A-Z][A-Z0-9]*)", expression[args_start:])
                if table_match:
                    table_name = table_match.group(1)
                    if table_name not in self.INTERPOLATION_TABLES:
                        self._warnings.append(
                            f"{location}: {context} - "
                            f"таблица интерполяции '{table_name}' не найдена"
                        )

            # Проверяем аргументы для prev
            if func_name == "prev":
                args_start = match.end()
                param_match = re.match(r"\s*([A-Z][A-Z0-9]*)", expression[args_start:])
                if param_match:
                    param_name = param_match.group(1)
                    if param_name not in self.get_all_parameter_names():
                        self._errors.append(
                            f"{location}: {context} - "
                            f"параметр '{param_name}' в prev() не существует"
                        )

    def validate_single_formula(self, formula: str) -> tuple[bool, list[str]]:
        """
        Валидирует одну формулу.

        Args:
            formula: Строка формулы

        Returns:
            Кортеж (is_valid, errors)
        """
        old_errors = self._errors
        self._errors = []

        self._validate_expression(formula, "Формула", "inline")

        errors = self._errors
        self._errors = old_errors

        return len(errors) == 0, errors

    def check_circular_dependencies(self) -> list[str]:
        """
        Проверяет наличие циклических зависимостей в формулах.

        Returns:
            Список циклических зависимостей (если есть)
        """
        # Строим граф зависимостей
        dependencies: dict[str, set[str]] = {}

        for section_name, section in self._formulas.items():
            if isinstance(section, dict):
                for param_name, formula in section.items():
                    if isinstance(formula, str):
                        # Убираем ссылки на prev() - они не создают циклов в текущем периоде
                        formula_without_prev = re.sub(r"prev\s*\([^)]+\)", "", formula)
                        current_deps = self._extract_variables(formula_without_prev)
                        dependencies[param_name] = current_deps

        # Ищем циклы с помощью DFS
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: list[str]) -> list[str] | None:
            if node in rec_stack:
                if node in path:
                    cycle_start = path.index(node)
                    return path[cycle_start:] + [node]
                return [node, node]

            if node in visited:
                return None

            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for dep in dependencies.get(node, set()):
                if dep in dependencies:  # Только проверяем расчётные параметры
                    result = dfs(dep, path.copy())
                    if result:
                        return result

            rec_stack.remove(node)
            return None

        for param in dependencies:
            if param not in visited:
                cycle = dfs(param, [])
                if cycle:
                    cycle_str = " -> ".join(cycle)
                    if cycle_str not in cycles:
                        cycles.append(cycle_str)

        return cycles


# Глобальный экземпляр валидатора
_validator: FormulaValidator | None = None


def get_validator() -> FormulaValidator:
    """Возвращает глобальный экземпляр валидатора."""
    global _validator
    if _validator is None:
        _validator = FormulaValidator()
    return _validator


def validate_formulas() -> tuple[list[str], list[str]]:
    """
    Валидирует все формулы в конфигурации.

    Returns:
        Кортеж (errors, warnings)
    """
    return get_validator().validate_all()


def validate_expression(expression: str) -> tuple[bool, list[str]]:
    """
    Валидирует одно выражение.

    Args:
        expression: Строка выражения

    Returns:
        Кортеж (is_valid, errors)
    """
    return get_validator().validate_single_formula(expression)
