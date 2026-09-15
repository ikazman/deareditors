from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("canteen", "0002_seed_2026_09_15_menu"),
    ]

    operations = [
        migrations.AddField(
            model_name="dailymenu",
            name="title",
            field=models.CharField(blank=True, default="", max_length=220, verbose_name="заголовок"),
        ),
        migrations.AddField(
            model_name="dailymenu",
            name="lead",
            field=models.TextField(blank=True, default="", verbose_name="лид"),
        ),
    ]
