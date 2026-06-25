from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("game", "0004_game_archive_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="game",
            name="finished_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Дата завершения",
            ),
        ),
    ]
