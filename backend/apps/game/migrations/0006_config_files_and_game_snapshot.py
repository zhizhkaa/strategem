# Generated manually for configuration editing support.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("game", "0005_game_finished_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="game",
            name="config_snapshot",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="YAML-конфигурация, с которой игра была начата",
                verbose_name="Снимок конфигурации",
            ),
        ),
        migrations.AddField(
            model_name="game",
            name="config_snapshot_label",
            field=models.CharField(
                default="Исходная",
                max_length=64,
                verbose_name="Версия конфигурации",
            ),
        ),
        migrations.CreateModel(
            name="ConfigFile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "filename",
                    models.CharField(
                        choices=[
                            ("parameters.yaml", "Параметры"),
                            ("formulas.yaml", "Формулы"),
                            ("decision_order.yaml", "Порядок решений"),
                            ("difficulties.yaml", "Сложности"),
                            ("interpolation.yaml", "Интерполяция"),
                        ],
                        max_length=64,
                        unique=True,
                        verbose_name="Файл",
                    ),
                ),
                ("content", models.TextField(verbose_name="Содержимое")),
                ("version", models.PositiveIntegerField(default=1, verbose_name="Версия")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Обновлено")),
            ],
            options={
                "verbose_name": "конфигурационный файл",
                "verbose_name_plural": "Конфигурационные файлы",
                "ordering": ["filename"],
            },
        ),
        migrations.CreateModel(
            name="GlobalGameSettings",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "use_team_passwords",
                    models.BooleanField(
                        default=True,
                        verbose_name="Использовать пароли команд",
                    ),
                ),
                (
                    "auto_calculate_decision_residuals",
                    models.BooleanField(
                        default=False,
                        verbose_name="Авторасчёт остаточных параметров",
                    ),
                ),
                (
                    "parallel_decision_mode",
                    models.BooleanField(
                        default=False,
                        verbose_name="Параллельный режим решений",
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Обновлено")),
            ],
            options={
                "verbose_name": "глобальные настройки игры",
                "verbose_name_plural": "Глобальные настройки игры",
            },
        ),
    ]
