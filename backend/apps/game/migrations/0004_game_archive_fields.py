from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("game", "0003_alter_game_total_periods"),
    ]

    operations = [
        migrations.AddField(
            model_name="game",
            name="archived_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Дата архивирования",
            ),
        ),
        migrations.AddField(
            model_name="game",
            name="is_archived",
            field=models.BooleanField(default=False, verbose_name="В архиве"),
        ),
    ]
