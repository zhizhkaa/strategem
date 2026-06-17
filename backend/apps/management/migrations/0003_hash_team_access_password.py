from django.contrib.auth.hashers import identify_hasher, make_password
from django.db import migrations, models


def hash_existing_team_passwords(apps, schema_editor):
    Team = apps.get_model("management", "Team")
    for team in Team.objects.exclude(access_password=""):
        try:
            identify_hasher(team.access_password)
        except ValueError:
            team.access_password = make_password(team.access_password)
            team.save(update_fields=["access_password"])


class Migration(migrations.Migration):

    dependencies = [
        ("management", "0002_team_access_password"),
    ]

    operations = [
        migrations.AlterField(
            model_name="team",
            name="access_password",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Хеш пароля, который команда вводит для входа в игру",
                max_length=128,
                verbose_name="Пароль команды",
            ),
        ),
        migrations.RunPython(hash_existing_team_passwords, migrations.RunPython.noop),
    ]
