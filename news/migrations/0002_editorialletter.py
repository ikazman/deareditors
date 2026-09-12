from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="EditorialLetter",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("body", models.TextField(verbose_name="сообщение")),
                ("sender_name", models.CharField(blank=True, max_length=120, verbose_name="имя")),
                ("contact", models.CharField(blank=True, max_length=240, verbose_name="контакт")),
                ("status", models.CharField(choices=[("new", "Новое"), ("reviewed", "Просмотрено")], default="new", max_length=12, verbose_name="статус")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="получено")),
                ("reviewed_at", models.DateTimeField(blank=True, null=True, verbose_name="просмотрено")),
                ("converted_article", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="source_letter", to="news.article", verbose_name="созданный черновик")),
            ],
            options={
                "verbose_name": "письмо в редакцию",
                "verbose_name_plural": "письма в редакцию",
                "ordering": ["-created_at"],
            },
        ),
    ]
