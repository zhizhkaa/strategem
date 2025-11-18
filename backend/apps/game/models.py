from pathlib import Path

import yaml
from django.db import models


class GameStatus(models.Model):
    """
    Модель статуса игры

    Attributes:
        id (int): (Unique) первичный ключ
        name (str): Название статуса (created, active, finished, paused, archived)
    """

    STATUS_CHOICES = [
        ("created", "Создана"),
        ("active", "Активна"),
        ("finished", "Завершена"),
        ("paused", "На паузе"),
        ("archived", "Архив"),
    ]

    name = models.CharField(
        choices=STATUS_CHOICES,
        max_length=16,
        default="created",
        verbose_name="Название статуса",
        help_text="Возможные статусы игры (по-умолчанию: Создана)",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Статус игры"
        verbose_name_plural = "Статусы игр"

    def __str__(self) -> str:
        return self.get_name_display()


class Game(models.Model):
    """
    Модель игры

    Attributes:
        id (int): (Unique) первичный ключ
        team (Team): Команда, участвующая в игре
        game_status (GameStatus): Текущий статус игры
        current_period (int): Текущий период игры
        total_periods (int): Максимальное число периодов
        created_at (datetime): Дата и время создания записи
        updated_at (datetime): Дата и время последнего обновления записи
    """

    team = models.ForeignKey(
        "management.Team",
        on_delete=models.CASCADE,
        related_name="games",
        verbose_name="Команда",
    )

    game_status = models.ForeignKey(
        GameStatus,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Статус игры",
        help_text="Текущий статус игры",
    )

    current_period = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Текущий период",
        help_text="Текущий период игры (начинается с 1)",
    )

    total_periods = models.PositiveSmallIntegerField(
        verbose_name="Всего периодов", help_text="Максимальное число периодов в игре"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Игра"
        verbose_name_plural = "Игры"

    def __str__(self) -> str:
        return f"Игра {self.id} | {self.team.name}"


def load_defaults():
    """Загружает дефолтные значения параметров из YAML файла"""
    yaml_path = Path(__file__).parent / "data" / "defaults.yaml"
    with open(yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_field_config(category: str, field_name: str):
    """Получает поля default и verbose_name из default"""
    defaults = load_defaults()
    return defaults[category][field_name]


DEFAULTS = load_defaults()


class GamePeriod(models.Model):
    period_number = models.PositiveSmallIntegerField(
        verbose_name="Период", help_text="Текущий номер периода"
    )
    game = models.ForeignKey(
        Game,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Игра",
        help_text="Игра, частью которой является период",
    )

    # Население
    P1 = models.FloatField(**get_field_config("population", "P1"))
    P2 = models.FloatField(**get_field_config("population", "P2"))
    P3 = models.FloatField(**get_field_config("population", "P3"))
    P4 = models.FloatField(**get_field_config("population", "P4"))
    P5 = models.FloatField(**get_field_config("population", "P5"))
    P6 = models.FloatField(**get_field_config("population", "P6"))
    P7 = models.FloatField(**get_field_config("population", "P7"))
    P8 = models.FloatField(**get_field_config("population", "P8"))
    P9 = models.FloatField(**get_field_config("population", "P9"))
    P10 = models.FloatField(**get_field_config("population", "P10"))
    P11 = models.FloatField(**get_field_config("population", "P11"))
    P12 = models.FloatField(**get_field_config("population", "P12"))
    P13 = models.FloatField(**get_field_config("population", "P13"))

    # Энергетика
    E1 = models.FloatField(**get_field_config("energy", "E1"))
    E2 = models.FloatField(**get_field_config("energy", "E2"))
    E3 = models.FloatField(**get_field_config("energy", "E3"))
    E4 = models.FloatField(**get_field_config("energy", "E4"))
    E5 = models.FloatField(**get_field_config("energy", "E5"))
    E6 = models.FloatField(**get_field_config("energy", "E6"))
    E7 = models.FloatField(**get_field_config("energy", "E7"))
    E8 = models.FloatField(**get_field_config("energy", "E8"))
    E9 = models.FloatField(**get_field_config("energy", "E9"))
    E10 = models.FloatField(**get_field_config("energy", "E10"))
    E11 = models.FloatField(**get_field_config("energy", "E11"))
    E12 = models.FloatField(**get_field_config("energy", "E12"))
    E13 = models.FloatField(**get_field_config("energy", "E13"))
    E14 = models.FloatField(**get_field_config("energy", "E14"))
    E15 = models.FloatField(**get_field_config("energy", "E15"))
    E16 = models.FloatField(**get_field_config("energy", "E16"))
    E17 = models.FloatField(**get_field_config("energy", "E17"))
    E18 = models.FloatField(**get_field_config("energy", "E18"))
    E19 = models.FloatField(**get_field_config("energy", "E19"))
    E20 = models.FloatField(**get_field_config("energy", "E20"))
    E21 = models.FloatField(**get_field_config("energy", "E21"))
    E22 = models.FloatField(**get_field_config("energy", "E22"))
    E23 = models.FloatField(**get_field_config("energy", "E23"))
    E24 = models.FloatField(**get_field_config("energy", "E24"))
    E25 = models.FloatField(**get_field_config("energy", "E25"))
    E26 = models.FloatField(**get_field_config("energy", "E26"))
    E27 = models.FloatField(**get_field_config("energy", "E27"))

    # Промышленность
    G1 = models.FloatField(**get_field_config("industry", "G1"))
    G2 = models.FloatField(**get_field_config("industry", "G2"))
    G3 = models.FloatField(**get_field_config("industry", "G3"))
    G4 = models.FloatField(**get_field_config("industry", "G4"))
    G5 = models.FloatField(**get_field_config("industry", "G5"))
    G6 = models.FloatField(**get_field_config("industry", "G6"))
    G7 = models.FloatField(**get_field_config("industry", "G7"))
    G8 = models.FloatField(**get_field_config("industry", "G8"))
    G9 = models.FloatField(**get_field_config("industry", "G9"))
    G10 = models.FloatField(**get_field_config("industry", "G10"))
    G11 = models.FloatField(**get_field_config("industry", "G11"))
    G12 = models.FloatField(**get_field_config("industry", "G12"))
    G13 = models.FloatField(**get_field_config("industry", "G13"))
    G14 = models.FloatField(**get_field_config("industry", "G14"))
    G15 = models.FloatField(**get_field_config("industry", "G15"))
    G16 = models.FloatField(**get_field_config("industry", "G16"))
    G17 = models.FloatField(**get_field_config("industry", "G17"))
    G18 = models.FloatField(**get_field_config("industry", "G18"))
    G19 = models.FloatField(**get_field_config("industry", "G19"))

    # Сельское хозяйство
    F1 = models.FloatField(**get_field_config("agriculture", "F1"))
    F2 = models.FloatField(**get_field_config("agriculture", "F2"))
    F3 = models.FloatField(**get_field_config("agriculture", "F3"))
    F4 = models.FloatField(**get_field_config("agriculture", "F4"))
    F5 = models.FloatField(**get_field_config("agriculture", "F5"))
    F6 = models.FloatField(**get_field_config("agriculture", "F6"))
    F7 = models.FloatField(**get_field_config("agriculture", "F7"))
    F8 = models.FloatField(**get_field_config("agriculture", "F8"))
    F9 = models.FloatField(**get_field_config("agriculture", "F9"))
    F10 = models.FloatField(**get_field_config("agriculture", "F10"))
    F11 = models.FloatField(**get_field_config("agriculture", "F11"))
    F12 = models.FloatField(**get_field_config("agriculture", "F12"))
    F13 = models.FloatField(**get_field_config("agriculture", "F13"))
    F14 = models.FloatField(**get_field_config("agriculture", "F14"))
    F15 = models.FloatField(**get_field_config("agriculture", "F15"))

    # Торговля и финансы
    TF1 = models.FloatField(**get_field_config("trade", "TF1"))
    TF2 = models.FloatField(**get_field_config("trade", "TF2"))
    TF3 = models.FloatField(**get_field_config("trade", "TF3"))
    TF4 = models.FloatField(**get_field_config("trade", "TF4"))
    TF5 = models.FloatField(**get_field_config("trade", "TF5"))
    TF6 = models.FloatField(**get_field_config("trade", "TF6"))
    TF7 = models.FloatField(**get_field_config("trade", "TF7"))
    TF8 = models.FloatField(**get_field_config("trade", "TF8"))
    TF9 = models.FloatField(**get_field_config("trade", "TF9"))
    TF10 = models.FloatField(**get_field_config("trade", "TF10"))
    TF11 = models.FloatField(**get_field_config("trade", "TF11"))
    TF12 = models.FloatField(**get_field_config("trade", "TF12"))
    TF13 = models.FloatField(**get_field_config("trade", "TF13"))
    TF14 = models.FloatField(**get_field_config("trade", "TF14"))
    TF15 = models.FloatField(**get_field_config("trade", "TF15"))
    TF16 = models.FloatField(**get_field_config("trade", "TF16"))
    TF17 = models.FloatField(**get_field_config("trade", "TF17"))
    TF18 = models.FloatField(**get_field_config("trade", "TF18"))

    # Прогресс принятия решений (0-4)
    decision_capital = models.IntegerField(
        default=0,
        verbose_name="Решения по капиталу",
        help_text="Уровень принятия решений по капиталовложениям (0-4)",
    )
    decision_energy = models.IntegerField(
        default=0,
        verbose_name="Решения по энергетике",
        help_text="Уровень принятия решений по энергетике (0-1)",
    )
    decision_finance = models.IntegerField(
        default=0,
        verbose_name="Решения по финансам",
        help_text="Уровень принятия решений по финансам (0-3)",
    )
    decision_import = models.IntegerField(
        default=0,
        verbose_name="Решения по импорту",
        help_text="Уровень принятия решений по импорту (0-3)",
    )

    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата создания периода"
    )

    class Meta:
        ordering = ["game", "period_number"]
        unique_together = ["game", "period_number"]
        verbose_name = "Период игры"
        verbose_name_plural = "Периоды игр"

    def __str__(self):
        return f"{self.name} | Период №{self.period_number}"
