from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("game", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="slot",
            field=models.CharField(
                blank=True,
                max_length=64,
                null=True,
                unique=True,
                verbose_name="Слот встроенного документа",
            ),
        ),
    ]
