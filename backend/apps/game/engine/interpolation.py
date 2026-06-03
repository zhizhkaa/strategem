"""
Модуль линейной интерполяции для игры Стратегема.

Загружает таблицы интерполяции из YAML-файла и предоставляет
функции для вычисления интерполированных значений.
"""

from __future__ import annotations

from pathlib import Path

import yaml


class Interpolator:
    """
    Класс для выполнения линейной интерполяции по таблицам.

    Таблицы загружаются из файла interpolation.yaml и содержат
    массивы x и y для каждой именованной таблицы.
    """

    _instance: Interpolator | None = None
    _tables: dict = {}

    def __new__(cls) -> "Interpolator":
        """Singleton pattern для кэширования загруженных таблиц."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_tables()
        return cls._instance

    def _load_tables(self) -> None:
        """Загружает таблицы интерполяции из YAML-файла."""
        yaml_path = Path(__file__).parent.parent / "data" / "interpolation.yaml"

        if not yaml_path.exists():
            raise FileNotFoundError(f"Файл интерполяции не найден: {yaml_path}")

        with open(yaml_path, "r", encoding="utf-8") as f:
            self._tables = yaml.safe_load(f)

    def reload_tables(self) -> None:
        """Перезагружает таблицы из файла (для разработки)."""
        self._load_tables()

    def get_table_names(self) -> list[str]:
        """Возвращает список имён доступных таблиц."""
        return list(self._tables.keys())

    def get_table(self, name: str) -> dict:
        """
        Возвращает таблицу по имени.

        Args:
            name: Имя таблицы (P1, P2, E1, E2, etc.)

        Returns:
            Словарь с ключами 'x', 'y', 'description'

        Raises:
            KeyError: Если таблица не найдена
        """
        if name not in self._tables:
            raise KeyError(f"Таблица интерполяции '{name}' не найдена")
        return self._tables[name]

    def get_all_tables(self) -> dict:
        """Возвращает все таблицы интерполяции."""
        return dict(self._tables)

    def interpolate(self, table_name: str, x: float) -> float:
        """
        Выполняет линейную интерполяцию по таблице.

        Если x выходит за пределы таблицы, возвращается
        ближайшее граничное значение (экстраполяция не выполняется).

        Args:
            table_name: Имя таблицы для интерполяции
            x: Значение аргумента

        Returns:
            Интерполированное значение y

        Raises:
            KeyError: Если таблица не найдена
            ValueError: Если таблица имеет некорректный формат
        """
        table = self.get_table(table_name)

        x_vals = table.get("x", [])
        y_vals = table.get("y", [])

        if not x_vals or not y_vals:
            raise ValueError(f"Таблица '{table_name}' не содержит данных x или y")

        if len(x_vals) != len(y_vals):
            raise ValueError(
                f"Таблица '{table_name}': длины x ({len(x_vals)}) "
                f"и y ({len(y_vals)}) не совпадают"
            )

        return self._linear_interpolate(x_vals, y_vals, x)

    @staticmethod
    def _linear_interpolate(
        x_vals: list[float], y_vals: list[float], x: float
    ) -> float:
        """
        Выполняет линейную интерполяцию между точками.

        Args:
            x_vals: Массив значений X (должен быть отсортирован по возрастанию)
            y_vals: Массив значений Y
            x: Значение аргумента для интерполяции

        Returns:
            Интерполированное значение
        """
        # Если x меньше минимального значения - возвращаем первый y
        if x <= x_vals[0]:
            return y_vals[0]

        # Если x больше максимального значения - возвращаем последний y
        if x >= x_vals[-1]:
            return y_vals[-1]

        # Ищем интервал, в который попадает x
        for i in range(len(x_vals) - 1):
            x0, x1 = x_vals[i], x_vals[i + 1]

            if x0 <= x <= x1:
                y0, y1 = y_vals[i], y_vals[i + 1]

                # Избегаем деления на ноль
                if x1 == x0:
                    return y0

                # Линейная интерполяция: y = y0 + (y1 - y0) * (x - x0) / (x1 - x0)
                return y0 + (y1 - y0) * (x - x0) / (x1 - x0)

        # Fallback (не должен достигаться)
        return y_vals[-1]

    def interpolate_with_bounds(
        self,
        table_name: str,
        x: float,
        min_result: float | None = None,
        max_result: float | None = None,
    ) -> float:
        """
        Интерполяция с ограничением результата.

        Args:
            table_name: Имя таблицы
            x: Значение аргумента
            min_result: Минимальное значение результата (или None)
            max_result: Максимальное значение результата (или None)

        Returns:
            Интерполированное значение в заданных границах
        """
        result = self.interpolate(table_name, x)

        if min_result is not None:
            result = max(result, min_result)

        if max_result is not None:
            result = min(result, max_result)

        return result


# Глобальный экземпляр для удобного доступа
_interpolator: Interpolator | None = None


def get_interpolator() -> Interpolator:
    """Возвращает глобальный экземпляр интерполятора."""
    global _interpolator
    if _interpolator is None:
        _interpolator = Interpolator()
    return _interpolator


def interpolate(table_name: str, x: float) -> float:
    """
    Удобная функция для интерполяции.

    Пример использования:
        from apps.game.engine.interpolation import interpolate
        result = interpolate("P1", 5.5)

    Args:
        table_name: Имя таблицы (P1, P2, E1, etc.)
        x: Значение аргумента

    Returns:
        Интерполированное значение
    """
    return get_interpolator().interpolate(table_name, x)
