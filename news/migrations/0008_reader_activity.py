from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0007_tarot_card_of_day"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ReaderArticleView",
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
                    "first_opened_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        verbose_name="первое открытие",
                    ),
                ),
                (
                    "last_opened_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        verbose_name="последнее открытие",
                    ),
                ),
                (
                    "open_count",
                    models.PositiveIntegerField(default=1, verbose_name="открытий"),
                ),
                (
                    "article",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reader_views",
                        to="news.article",
                        verbose_name="материал",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="article_views",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="читатель",
                    ),
                ),
            ],
            options={
                "verbose_name": "просмотр материала читателем",
                "verbose_name_plural": "просмотры материалов читателями",
                "ordering": ["-last_opened_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="ReaderDailyVisit",
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
                    "visit_date",
                    models.DateField(
                        default=django.utils.timezone.localdate,
                        verbose_name="дата посещения",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="зафиксировано"),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reader_daily_visits",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="читатель",
                    ),
                ),
            ],
            options={
                "verbose_name": "день посещения читателя",
                "verbose_name_plural": "дни посещений читателей",
                "ordering": ["-visit_date", "-id"],
            },
        ),
        migrations.AddConstraint(
            model_name="readerarticleview",
            constraint=models.UniqueConstraint(
                fields=("user", "article"),
                name="unique_reader_article_view",
            ),
        ),
        migrations.AddConstraint(
            model_name="readerdailyvisit",
            constraint=models.UniqueConstraint(
                fields=("user", "visit_date"),
                name="unique_reader_daily_visit",
            ),
        ),
    ]
