from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


def current_year() -> int:
    return timezone.now().year


class Faculty(models.Model):
    """
    Модель факультета

    Attributes:
        id (int): (Unique) первичный ключ
        name (str): (Unique) Название факультета
        created_at (datetime): Дата и время создания записи
        updated_at (datetime): Дата и время последнего обновления записи
    """

    name = models.CharField(max_length=255, unique=True, verbose_name="Название")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        ordering = ["name"]
        verbose_name = "факультет"
        verbose_name_plural = "Факультеты"

    def __str__(self) -> str:
        return str(self.name)


class Group(models.Model):
    """
    Модель студенческой группы

    Attributes:
        id (int): (Unique) первичный ключ
        name (str): Название группы
        faculty (Faculty): Факультет группы
        year (int): Год участия в игре
        created_at (datetime): Дата и время создания записи
        updated_at (datetime): Дата и время последнего обновления записи
    """

    name = models.CharField(max_length=255, verbose_name="Название")
    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.CASCADE,
        related_name="groups",
        verbose_name="Факультет",
    )
    year = models.IntegerField(
        default=current_year, validators=[MinValueValidator(2000)], verbose_name="Год"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        ordering = ["faculty__name", "year", "name"]
        unique_together = ["name", "faculty", "year"]
        verbose_name = "студенческую группу"
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

    name = models.CharField(max_length=255, verbose_name="Название")
    group = models.ForeignKey(
        Group, on_delete=models.CASCADE, related_name="teams", verbose_name="Группа"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        ordering = ["group__faculty__name", "group__year", "group__name", "name"]
        unique_together = ["name", "group"]
        verbose_name = "команду"
        verbose_name_plural = "Команды"

    def __str__(self) -> str:
        return str(self.name)
