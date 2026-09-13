from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0008_reader_activity"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ReaderProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "ticket_number",
                    models.CharField(
                        editable=False,
                        max_length=10,
                        unique=True,
                        verbose_name="номер билета",
                    ),
                ),
                (
                    "issued_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        verbose_name="выдан",
                    ),
                ),
                (
                    "cover_key",
                    models.CharField(
                        default="classic",
                        max_length=32,
                        verbose_name="обложка",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reader_profile",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="читатель",
                    ),
                ),
            ],
            options={
                "verbose_name": "читательский билет",
                "verbose_name_plural": "читательские билеты",
            },
        ),
    ]
