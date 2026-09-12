from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="Article",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=220, verbose_name="заголовок")),
                ("slug", models.SlugField(allow_unicode=True, blank=True, max_length=240, unique=True, verbose_name="адрес")),
                ("lead", models.TextField(blank=True, verbose_name="лид")),
                ("body", models.TextField(verbose_name="текст")),
                ("author_name", models.CharField(default="Дорогая редакция", max_length=120, verbose_name="автор")),
                ("status", models.CharField(choices=[("draft", "Черновик"), ("published", "Опубликовано")], default="draft", max_length=12, verbose_name="статус")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="создано")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="изменено")),
                ("published_at", models.DateTimeField(blank=True, null=True, verbose_name="опубликовано")),
            ],
            options={
                "verbose_name": "публикация",
                "verbose_name_plural": "публикации",
                "ordering": ["-published_at", "-created_at"],
            },
        ),
    ]
