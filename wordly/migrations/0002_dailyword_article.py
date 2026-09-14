from django.db import migrations, models
import django.db.models.deletion


def create_wordly_articles(apps, schema_editor):
    DailyWord = apps.get_model("wordly", "DailyWord")
    Article = apps.get_model("news", "Article")

    for daily_word in DailyWord.objects.filter(article__isnull=True).iterator():
        article = Article.objects.create(
            title="Редакция загадала слово",
            slug=f"wordly-{daily_word.date:%Y-%m-%d}",
            rubric="Вордли",
            lead="Пять букв. Шесть попыток.",
            body="",
            author_name="Дорогая редакция",
            status="draft",
        )
        daily_word.article_id = article.pk
        daily_word.save(update_fields=["article"])


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0011_achievement_snapshots"),
        ("wordly", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="dailyword",
            name="article",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="wordly_daily_word",
                to="news.article",
                verbose_name="публикация",
            ),
        ),
        migrations.RunPython(create_wordly_articles, migrations.RunPython.noop),
    ]
