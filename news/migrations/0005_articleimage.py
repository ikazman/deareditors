import uuid

import django.db.models.deletion
from django.db import migrations, models

import news.models


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0004_mcpaccesskey"),
    ]

    operations = [
        migrations.CreateModel(
            name="ArticleImage",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("file", models.FileField(max_length=255, upload_to=news.models.article_image_upload_path, verbose_name="изображение")),
                ("caption", models.CharField(blank=True, max_length=500, verbose_name="подпись")),
                ("alt_text", models.CharField(max_length=240, verbose_name="описание")),
                ("layout", models.CharField(choices=[("measure", "В колонку"), ("wide", "Шире текста")], default="measure", max_length=12, verbose_name="ширина")),
                ("content_type", models.CharField(editable=False, max_length=32, verbose_name="тип файла")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="загружено")),
                ("article", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="images", to="news.article", verbose_name="материал")),
            ],
            options={
                "verbose_name": "изображение материала",
                "verbose_name_plural": "изображения материала",
                "ordering": ["created_at"],
            },
        ),
    ]
