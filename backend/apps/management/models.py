from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Faculty(models.Model):
    """
    Модель факультета

    Attributes:
        id (int): (Unique) первичный ключ
        name (str): (Unique) Название факультета
        created_at (datetime): Дата и время создания записи
        updated_at (datetime): Дата и время последнего обновления записи
    """

    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Факультет"
        verbose_name_plural = "Факультеты"

    def __str__(self) -> str:
        return str(self.name)


def current_year() -> int:
    return int(timezone.now().year)


class Group(models.Model):
    """
    Модель группы

    Attributes:
        id (int): (Unique) первичный ключ
        name (str): Название группы
        faculty (Faculty): Факультет группы
        year (int): Год участия в игре
        created_at (datetime): Дата и время создания записи
        updated_at (datetime): Дата и время последнего обновления записи
    """

    name = models.CharField(max_length=255)
    faculty = models.ForeignKey(
        Faculty, on_delete=models.CASCADE, related_name="groups"
    )
    year = models.IntegerField(
        default=current_year, validators=[MinValueValidator(2000)]
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["faculty__name", "name", "year"]
        unique_together = ["name", "faculty", "year"]
        verbose_name = "Студенческая группа"
        verbose_name_plural = "Студенческие группы"

    def __str__(self) -> str:
        return f"{self.name} | {self.year}"


class Team(models.Model):
    """
    Модель команды

    Attributes:
        id (int): (Unique) первичный ключ
        name (str): Название команды
        group (Group): Студенческая группа команды
        created_at (datetime): Дата и время создания записи
        updated_at (datetime): Дата и время последнего обновления записи
    """

    name = models.CharField(max_length=255)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="teams")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["group__faculty__name", "group__name", "name"]
        unique_together = ["name", "group"]
        verbose_name = "Команда"
        verbose_name_plural = "Команды"

    def __str__(self) -> str:
        return str(self.name)
