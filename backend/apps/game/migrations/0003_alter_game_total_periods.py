from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("game", "0002_document_slot"),
    ]

    operations = [
        migrations.AlterField(
            model_name="game",
            name="total_periods",
            field=models.PositiveSmallIntegerField(
                default=10,
                help_text="Количество периодов в игре (10 или 12)",
                verbose_name="Всего периодов",
            ),
        ),
    ]
