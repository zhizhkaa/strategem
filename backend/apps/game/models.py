"""
Модели игры Стратегема.

Включает:
- GameStatus: статусы игры
- Game: основная модель игры
- GamePeriod: период игры с параметрами
- Document: загруженный файл документации
"""

from pathlib import Path
from typing import Any

import yaml
from apps.management.models import Team
from django.core.exceptions import ValidationError
from django.db import models


def load_defaults() -> dict:
    """Загружает дефолтные значения параметров из YAML файла."""
    yaml_path = Path(__file__).parent / "data" / "parameters.yaml"
    if not yaml_path.exists():
        return {}
    with open(yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_all_parameters() -> dict[str, dict]:
    """Возвращает все параметры с их конфигурацией."""
    defaults = load_defaults()
    result = {}
    for category in defaults.values():
        if isinstance(category, dict):
            result.update(category)
    return result


PARAMETERS_CONFIG = get_all_parameters()
ALLOWED_TOTAL_PERIODS = (10, 12)


class GameStatus(models.TextChoices):
    """Статусы игры."""

    CREATED = "created", "Создана"
    ACTIVE = "active", "Активна"
    FINISHED = "finished", "Завершена"
    PAUSED = "paused", "На паузе"


class GameDifficulty(models.TextChoices):
    """Режимы сложности игры."""

    SIMPLE = "simple", "Simple"
    STANDARD = "standard", "Standard"
    TOUGH = "tough", "Tough"
    VERYHARD = "veryhard", "Very Hard"
    HIGHEQ = "higheq", "High EQ"


class Game(models.Model):
    """
    Модель игры.

    Attributes:
        id (int): Первичный ключ
        team (Team): Команда, участвующая в игре
        status (str): Текущий статус игры
        current_period (int): Текущий период игры
        total_periods (int): Максимальное число периодов
        decision_capital (int): Уровень решений по капиталу (0-4)
        decision_energy (int): Уровень решений по энергетике (0-1)
        decision_finance (int): Уровень решений по финансам (0-3)
        decision_import (int): Уровень решений по импорту (0-3)
        created_at (datetime): Дата создания
        updated_at (datetime): Дата обновления
    """

    team = models.OneToOneField(
        Team,
        on_delete=models.CASCADE,
        related_name="game",
        verbose_name="Команда",
        help_text="Одна команда может иметь только одну активную игру",
    )

    status = models.CharField(
        max_length=16,
        choices=GameStatus.choices,
        default=GameStatus.CREATED,
        verbose_name="Статус",
    )

    current_period = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Текущий период",
    )

    total_periods = models.PositiveSmallIntegerField(
        default=10,
        verbose_name="Всего периодов",
        help_text="Количество периодов в игре (10 или 12)",
    )

    difficulty = models.CharField(
        max_length=16,
        choices=GameDifficulty.choices,
        default=GameDifficulty.STANDARD,
        verbose_name="Сложность",
    )

    # Состояния решений
    decision_capital = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Решения по капиталу",
        help_text="Уровень принятия решений по капиталовложениям (0-4)",
    )

    decision_energy = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Решения по энергетике",
        help_text="Уровень принятия решений по энергетике (0-1)",
    )

    decision_finance = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Решения по финансам",
        help_text="Уровень принятия финансовых решений (0-3)",
    )

    decision_import = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Решения по импорту",
        help_text="Уровень принятия решений по импорту (0-3)",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Игра"
        verbose_name_plural = "Игры"

    def __str__(self) -> str:
        return f"Игра #{self.id} | {self.team.name}"

    def clean(self) -> None:
        """Валидация модели."""
        if self.total_periods not in ALLOWED_TOTAL_PERIODS:
            allowed = ", ".join(str(periods) for periods in ALLOWED_TOTAL_PERIODS)
            raise ValidationError(
                {
                    "total_periods": f"Количество периодов должно быть одним из: {allowed}"
                }
            )

        if self.current_period > self.total_periods:
            raise ValidationError(
                {"current_period": "Текущий период не может превышать общее количество"}
            )

    def reset_decisions(self) -> None:
        """Сбрасывает состояния решений для нового периода."""
        self.decision_capital = 0
        self.decision_energy = 0
        self.decision_finance = 0
        self.decision_import = 0

    def get_decision_states(self) -> dict[str, int]:
        """Возвращает текущие состояния решений."""
        return {
            "capital": self.decision_capital,
            "energy": self.decision_energy,
            "finance": self.decision_finance,
            "import": self.decision_import,
        }

    def set_decision_states(self, states: dict[str, int]) -> None:
        """Устанавливает состояния решений из словаря."""
        if "capital" in states:
            self.decision_capital = states["capital"]
        if "energy" in states:
            self.decision_energy = states["energy"]
        if "finance" in states:
            self.decision_finance = states["finance"]
        if "import" in states:
            self.decision_import = states["import"]

    def get_current_period_obj(self) -> "GamePeriod":
        """Возвращает объект текущего периода."""
        period, _ = GamePeriod.objects.get_or_create(
            game=self,
            period_number=self.current_period,
            defaults=self._get_period_defaults(),
        )
        return period

    def _get_period_defaults(self) -> dict[str, Any]:
        """Возвращает значения по умолчанию для нового периода."""
        from .engine import get_calculator

        return get_calculator().get_initial_parameters(self.difficulty)

    def _get_period_reset_parameter_names(self) -> set[str]:
        """Параметры решений, которые не переносятся в новый период."""
        from .engine import get_calculator

        calculator = get_calculator()
        return set(calculator.get_input_parameters()) | set(
            calculator.get_decision_parameter_names()
        )

    def _repair_negative_decision_residuals(
        self, period: "GamePeriod", params: dict[str, float]
    ) -> None:
        """Исправляет ранее сохранённые отрицательные остаточные автопараметры."""
        repaired_fields = []

        for param_name in ("P10", "P13", "E23", "E25", "F15", "TF15", "TF18"):
            if params.get(param_name, 0) < 0:
                params[param_name] = 0.0
                setattr(period, param_name, 0.0)
                repaired_fields.append(param_name)

        if repaired_fields:
            period.save(update_fields=repaired_fields)

    def get_history(self) -> list[dict[str, float]]:
        """Возвращает историю параметров за все предыдущие периоды."""
        periods = GamePeriod.objects.filter(
            game=self, period_number__lt=self.current_period
        ).order_by("period_number")

        history = []
        for period in periods:
            history.append(period.get_parameters())

        return history

    def can_advance_period(self) -> bool:
        """Проверяет, можно ли перейти к следующему периоду."""
        # Все решения должны быть приняты
        return (
            self.decision_capital >= 4
            and self.decision_energy >= 1
            and self.decision_finance >= 3
            and self.decision_import >= 3
        )

    def advance_period(self) -> bool:
        """
        Переходит к следующему периоду.

        Returns:
            True если переход успешен, False если игра завершена
        """
        from .engine import get_calculator

        if self.current_period >= self.total_periods:
            self.status = GameStatus.FINISHED
            self.save()
            return False

        # Получаем текущий период и историю
        current_period = self.get_current_period_obj()
        current_params = current_period.get_parameters()
        self._repair_negative_decision_residuals(current_period, current_params)
        history = self.get_history()

        # Рассчитываем новые параметры
        calculator = get_calculator()
        new_params = calculator.calculate_next_period(
            current_params,
            history,
            recalculate_decisions=False,
        )
        for param_name in self._get_period_reset_parameter_names():
            if param_name in new_params:
                new_params[param_name] = 0.0

        # Создаём новый период
        self.current_period += 1
        GamePeriod.objects.create(
            game=self,
            period_number=self.current_period,
            **{k: v for k, v in new_params.items() if k in PARAMETERS_CONFIG},
        )

        # Сбрасываем решения
        self.reset_decisions()
        self.save()

        return True


class GamePeriod(models.Model):
    """
    Период игры с параметрами.

    Хранит все 74 параметра игры для конкретного периода.
    """

    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name="periods",
        verbose_name="Игра",
    )

    period_number = models.PositiveSmallIntegerField(
        verbose_name="Номер периода",
    )

    # ========================================
    # НАСЕЛЕНИЕ (P1-P13)
    # ========================================
    P1 = models.FloatField(default=200, verbose_name="Численность населения")
    P2 = models.FloatField(default=3300, verbose_name="Всего продовольствия")
    P3 = models.FloatField(default=3500, verbose_name="Всего товаров")
    P4 = models.FloatField(default=2, verbose_name="Продовольствие на душу населения")
    P5 = models.FloatField(default=18, verbose_name="Уровень смертности")
    P6 = models.FloatField(default=2, verbose_name="Товары на душу населения")
    P7 = models.FloatField(default=2.25, verbose_name="Услуги на душу населения")
    P8 = models.FloatField(default=41, verbose_name="Уровень рождаемости")
    P9 = models.FloatField(default=0, verbose_name="Продовольствие для населения")
    P10 = models.FloatField(default=0, verbose_name="Продовольствие на экспорт")
    P11 = models.FloatField(default=0, verbose_name="Товары для населения")
    P12 = models.FloatField(default=0, verbose_name="Товары для капиталовложения")
    P13 = models.FloatField(default=0, verbose_name="Товары на экспорт")

    # ========================================
    # ЭНЕРГЕТИКА (E1-E27)
    # ========================================
    E1 = models.FloatField(default=160, verbose_name="Выбытие капитала для энергии")
    E2 = models.FloatField(default=640, verbose_name="Новый капитал для энергии")
    E3 = models.FloatField(default=800, verbose_name="Основной капитал для энергии")
    E4 = models.FloatField(default=0, verbose_name="Выбытие капитала энергосбережения")
    E5 = models.FloatField(default=0, verbose_name="Новый капитал энергосбережения")
    E6 = models.FloatField(default=0, verbose_name="Основной капитал энергосбережения")
    E7 = models.FloatField(default=15000, verbose_name="Всего энергоресурсов")
    E8 = models.FloatField(default=0.2, verbose_name="Энергоресурсы на единицу товаров")
    E9 = models.FloatField(default=400, verbose_name="Энергоресурсы для населения")
    E10 = models.FloatField(
        default=1.0, verbose_name="Коэффициент потребления ресурсов"
    )
    E11 = models.FloatField(
        default=12.5, verbose_name="Энергоресурсы на единицу с/х капитала"
    )
    E12 = models.FloatField(default=10000, verbose_name="Потребность в энергии для с/х")
    E13 = models.FloatField(
        default=20, verbose_name="Энергоресурсы на единицу пром. капитала"
    )
    E14 = models.FloatField(
        default=6000, verbose_name="Потребность в энергии для товаров"
    )
    E15 = models.FloatField(
        default=16000, verbose_name="Потребность в энергии для производства"
    )
    E16 = models.FloatField(
        default=17.5, verbose_name="Генерация энергии на единицу капитала"
    )
    E17 = models.FloatField(default=14000, verbose_name="Производство энергоресурсов")
    E18 = models.FloatField(
        default=0, verbose_name="Энергоресурсы на экспорт (прошлый период)"
    )
    E19 = models.FloatField(default=1000, verbose_name="Импорт энергоресурсов")
    E20 = models.FloatField(default=0, verbose_name="Энергоресурсы для населения")
    E21 = models.FloatField(default=0, verbose_name="Энергоресурсы на экспорт")
    E22 = models.FloatField(default=0, verbose_name="Энергоресурсы в резерв")
    E23 = models.FloatField(default=0, verbose_name="Энергоресурсы для производства")
    E24 = models.FloatField(
        default=0, verbose_name="Энергия для производства продовольствия"
    )
    E25 = models.FloatField(default=0, verbose_name="Энергия для производства товаров")
    E26 = models.FloatField(
        default=0, verbose_name="Капиталовложения в генерацию энергии"
    )
    E27 = models.FloatField(
        default=0, verbose_name="Капиталовложения в энергосбережение"
    )

    # ========================================
    # ПРОМЫШЛЕННОСТЬ (G1-G19)
    # ========================================
    G1 = models.FloatField(default=60, verbose_name="Выбытие капитала для товаров")
    G2 = models.FloatField(default=240, verbose_name="Новый капитал для товаров")
    G3 = models.FloatField(default=300, verbose_name="Основной капитал для товаров")
    G4 = models.FloatField(default=50, verbose_name="Выбытие капитала сферы услуг")
    G5 = models.FloatField(default=400, verbose_name="Новый капитал сферы услуг")
    G6 = models.FloatField(default=450, verbose_name="Основной капитал сферы услуг")
    G7 = models.FloatField(default=6, verbose_name="Капитал на 1 рабочего")
    G8 = models.FloatField(
        default=5, verbose_name="Коэффициент производительности труда"
    )
    G9 = models.FloatField(default=2.25, verbose_name="Услуги на душу населения")
    G10 = models.FloatField(
        default=2.13, verbose_name="Коэффициент производительности от услуг"
    )
    G11 = models.FloatField(
        default=1, verbose_name="Коэффициент использования капитала"
    )
    G12 = models.FloatField(
        default=3000, verbose_name="Фактическое производство товаров"
    )
    G13 = models.FloatField(default=0, verbose_name="Экспорт товаров (прошлый период)")
    G14 = models.FloatField(default=500, verbose_name="Импорт товаров")
    G15 = models.FloatField(default=3100, verbose_name="Плановое производство товаров")
    G16 = models.FloatField(default=3500, verbose_name="Всего товаров")
    G17 = models.FloatField(
        default=430, verbose_name="Выбытие капитала во всех секторах"
    )
    G18 = models.FloatField(
        default=0, verbose_name="Капиталовложения в производство товаров"
    )
    G19 = models.FloatField(default=0, verbose_name="Капиталовложения в сферу услуг")

    # ========================================
    # СЕЛЬСКОЕ ХОЗЯЙСТВО (F1-F15)
    # ========================================
    F1 = models.FloatField(default=160, verbose_name="Выбытие капитала с/х")
    F2 = models.FloatField(default=640, verbose_name="Новый капитал с/х")
    F3 = models.FloatField(default=800, verbose_name="Основной капитал с/х")
    F4 = models.FloatField(default=0, verbose_name="Выбытие природоохранного капитала")
    F5 = models.FloatField(default=0, verbose_name="Новый природоохранный капитал")
    F6 = models.FloatField(default=0, verbose_name="Основной природоохранный капитал")
    F7 = models.FloatField(default=0.69, verbose_name="Состояние окружающей среды")
    F8 = models.FloatField(
        default=0.8, verbose_name="Отношение капитала с/х к площади угодий"
    )
    F9 = models.FloatField(
        default=3450, verbose_name="Плановое производство продовольствия"
    )
    F10 = models.FloatField(
        default=1, verbose_name="Коэффициент использования с/х капитала"
    )
    F11 = models.FloatField(default=3300, verbose_name="Производство продовольствия")
    F12 = models.FloatField(
        default=1550, verbose_name="Экспорт продовольствия (прошлый период)"
    )
    F13 = models.FloatField(default=0, verbose_name="Импорт продовольствия")
    F14 = models.FloatField(default=0, verbose_name="Капиталовложения в с/х")
    F15 = models.FloatField(default=0, verbose_name="Капиталовложения в защиту среды")

    # ========================================
    # ТОРГОВЛЯ И ФИНАНСЫ (TF1-TF18)
    # ========================================
    TF1 = models.FloatField(default=0, verbose_name="Внешний долг")
    TF2 = models.FloatField(default=10, verbose_name="Процентная ставка")
    TF3 = models.FloatField(default=1, verbose_name="Коэффициент девальвации")
    TF4 = models.FloatField(default=0, verbose_name="Проценты за кредит")
    TF5 = models.FloatField(default=1000, verbose_name="Максимально возможный кредит")
    TF6 = models.FloatField(default=1, verbose_name="Цена на импорт энергии")
    TF7 = models.FloatField(default=1.1, verbose_name="Цена на импорт продовольствия")
    TF8 = models.FloatField(default=1.1, verbose_name="Цена на импорт товаров")
    TF9 = models.FloatField(default=0, verbose_name="Иностранная помощь")
    TF10 = models.FloatField(default=0, verbose_name="Валюта от экспорта энергии")
    TF11 = models.FloatField(default=0, verbose_name="Валюта от экспорта товаров")
    TF12 = models.FloatField(
        default=0, verbose_name="Валюта от экспорта продовольствия"
    )
    TF13 = models.FloatField(default=0, verbose_name="Новый кредит")
    TF14 = models.FloatField(default=0, verbose_name="Выплаты по долгу")
    TF15 = models.FloatField(default=0, verbose_name="Валюта для импорта")
    TF16 = models.FloatField(default=0, verbose_name="Валюта для импорта энергии")
    TF17 = models.FloatField(default=0, verbose_name="Валюта для импорта товаров")
    TF18 = models.FloatField(
        default=0, verbose_name="Валюта для импорта продовольствия"
    )

    # Список параметров, явно введённых пользователем
    # Нужен для корректной проверки заполненности этапа,
    # когда пользователь вводит значение равное default (например, 0)
    user_inputs = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Введённые пользователем параметры",
        help_text="Список параметров, которые были явно введены пользователем",
    )

    # Состояние валидации — хранится на сервере для синхронизации между всеми экранами.
    # Структура: {
    #   "errors": ["E24", "G18"],          # параметры с ошибками (красная подсветка)
    #   "incomplete": ["TF13"],             # незаполненные параметры (жёлтая подсветка)
    #   "by_minister": {                    # разбивка по министрам
    #     "energy": {"errors": ["E24"], "incomplete": []},
    #     ...
    #   },
    #   "last_validated": "2026-04-03T..."  # ISO-строка времени последней валидации
    # }
    validation_state = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Состояние валидации",
        help_text="Ошибки и незаполненные параметры, синхронизируемые между экранами",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")

    class Meta:
        ordering = ["game", "period_number"]
        unique_together = ["game", "period_number"]
        verbose_name = "Период игры"
        verbose_name_plural = "Периоды игр"

    def __str__(self) -> str:
        return f"Период {self.period_number} | {self.game}"

    def get_parameters(self) -> dict[str, float]:
        """Возвращает все параметры как словарь."""
        params = {}
        for param_name in PARAMETERS_CONFIG.keys():
            if hasattr(self, param_name):
                params[param_name] = getattr(self, param_name)
        return params

    def set_parameters(self, params: dict[str, float]) -> None:
        """Устанавливает параметры из словаря."""
        for param_name, value in params.items():
            if hasattr(self, param_name):
                setattr(self, param_name, value)

    def set_parameter(
        self, param_name: str, value: float, mark_as_user_input: bool = True
    ) -> bool:
        """
        Устанавливает значение одного параметра.

        Args:
            param_name: Имя параметра
            value: Значение параметра
            mark_as_user_input: Если True, помечает параметр как введённый пользователем

        Returns:
            True если параметр существует и установлен
        """
        if hasattr(self, param_name) and param_name in PARAMETERS_CONFIG:
            setattr(self, param_name, value)
            if mark_as_user_input and param_name not in self.user_inputs:
                self.user_inputs = list(self.user_inputs) + [param_name]
            return True
        return False

    def is_user_input(self, param_name: str) -> bool:
        """
        Проверяет, был ли параметр явно введён пользователем.

        Returns:
            True если параметр был введён пользователем
        """
        return param_name in self.user_inputs

    def mark_as_user_input(self, param_name: str) -> None:
        """Помечает параметр как введённый пользователем."""
        if param_name not in self.user_inputs:
            self.user_inputs = list(self.user_inputs) + [param_name]

    def get_parameter(self, param_name: str) -> float | None:
        """
        Возвращает значение одного параметра.

        Returns:
            Значение параметра или None если не существует
        """
        if hasattr(self, param_name) and param_name in PARAMETERS_CONFIG:
            return getattr(self, param_name)
        return None


class Document(models.Model):
    """Загруженный файл документации."""

    SCOPE_CHOICES = [
        ("general", "Общий"),
        ("minister", "Министр"),
    ]

    title = models.CharField(max_length=255, verbose_name="Название")
    file = models.FileField(upload_to="documents/", verbose_name="Файл")
    slot = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        unique=True,
        verbose_name="Слот встроенного документа",
    )
    scope = models.CharField(
        max_length=10,
        choices=SCOPE_CHOICES,
        default="general",
        verbose_name="Область",
    )
    minister = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Министр",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Документ"
        verbose_name_plural = "Документы"

    def __str__(self):
        return self.title
