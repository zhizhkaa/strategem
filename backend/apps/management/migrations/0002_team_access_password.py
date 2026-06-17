from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("management", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="team",
            name="access_password",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Пароль, который команда вводит для входа в игру",
                max_length=32,
                verbose_name="Пароль команды",
            ),
        ),
    ]
