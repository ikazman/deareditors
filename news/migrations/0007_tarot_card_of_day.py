from django.db import migrations, models
import django.db.models.deletion
import news.models


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0006_articleimage_marker_index"),
    ]

    operations = [
        migrations.AddField(
            model_name="article",
            name="rubric",
            field=models.CharField(blank=True, max_length=80, verbose_name="рубрика"),
        ),
        migrations.CreateModel(
            name="TarotCard",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True, verbose_name="карта")),
                ("description", models.TextField(blank=True, verbose_name="описание")),
                ("check_words", models.TextField(blank=True, verbose_name="ключевые слова")),
                ("prophecy", models.TextField(blank=True, verbose_name="прогноз")),
                ("meaning_straight", models.TextField(verbose_name="прямое значение")),
                ("meaning_reversed", models.TextField(verbose_name="перевернутое значение")),
                ("image", models.FileField(max_length=255, upload_to=news.models.tarot_card_upload_path, verbose_name="изображение карты")),
            ],
            options={
                "verbose_name": "карта Таро",
                "verbose_name_plural": "карты Таро",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="TarotDraw",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("draw_date", models.DateField(unique=True, verbose_name="дата")),
                ("question", models.CharField(max_length=240, verbose_name="вопрос")),
                ("card_name", models.CharField(max_length=120, verbose_name="карта")),
                ("position", models.CharField(choices=[("straight", "Прямая"), ("reversed", "Перевернутая")], max_length=12, verbose_name="положение")),
                ("check_words", models.TextField(blank=True, verbose_name="ключевые слова")),
                ("prophecy", models.TextField(blank=True, verbose_name="прогноз")),
                ("meaning", models.TextField(verbose_name="значение")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="создано")),
                ("article", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="tarot_draw", to="news.article", verbose_name="черновик")),
            ],
            options={
                "verbose_name": "карта дня",
                "verbose_name_plural": "карты дня",
                "ordering": ["-draw_date"],
            },
        ),
    ]
