from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DailyWord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField(unique=True, verbose_name="дата")),
                ("word", models.CharField(max_length=5, verbose_name="слово")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="создано")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="изменено")),
            ],
            options={
                "verbose_name": "слово дня",
                "verbose_name_plural": "слова дня",
                "ordering": ["-date"],
            },
        ),
        migrations.CreateModel(
            name="WordlyGame",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("guesses", models.JSONField(default=list, verbose_name="попытки")),
                ("won", models.BooleanField(default=False, verbose_name="угадано")),
                ("completed_at", models.DateTimeField(blank=True, null=True, verbose_name="завершено")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="начато")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="изменено")),
                (
                    "daily_word",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="games", to="wordly.dailyword", verbose_name="слово дня"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="wordly_games", to=settings.AUTH_USER_MODEL, verbose_name="читатель"),
                ),
            ],
            options={
                "verbose_name": "партия Вордли",
                "verbose_name_plural": "партии Вордли",
                "ordering": ["-daily_word__date", "-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="wordlygame",
            constraint=models.UniqueConstraint(fields=("user", "daily_word"), name="unique_wordly_game_per_reader_and_day"),
        ),
    ]
