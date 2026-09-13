from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("news", "0009_reader_profile"),
    ]

    operations = [
        migrations.AddField(
            model_name="editorialletter",
            name="submitted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="editorial_letters",
                to=settings.AUTH_USER_MODEL,
                verbose_name="отправитель",
            ),
        ),
        migrations.CreateModel(
            name="AchievementUnlock",
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
                    "code",
                    models.CharField(
                        choices=[
                            ("correspondent_iii", "Корреспондент III степени"),
                            ("correspondent_ii", "Корреспондент II степени"),
                        ],
                        max_length=32,
                        verbose_name="отметка",
                    ),
                ),
                (
                    "unlocked_at",
                    models.DateTimeField(default=django.utils.timezone.now, verbose_name="зафиксировано"),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reader_marks",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="читатель",
                    ),
                ),
            ],
            options={
                "verbose_name": "отметка редакции",
                "verbose_name_plural": "отметки редакции",
                "ordering": ["unlocked_at", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="achievementunlock",
            constraint=models.UniqueConstraint(
                fields=("user", "code"),
                name="unique_reader_achievement_unlock",
            ),
        ),
    ]
