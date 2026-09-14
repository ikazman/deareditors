from datetime import datetime, time

from django.db import migrations
from django.utils import timezone


WORDLY_TITLE = "Редакция загадала слово"
WORDLY_RUBRIC = "Вордли"
WORDLY_LEAD = "Пять букв. Шесть попыток."


def publish_wordly_entries(apps, schema_editor):
    DailyWord = apps.get_model("wordly", "DailyWord")
    Article = apps.get_model("news", "Article")
    current_timezone = timezone.get_current_timezone()

    for daily_word in DailyWord.objects.all().iterator():
        published_at = timezone.make_aware(
            datetime.combine(daily_word.date, time.min),
            current_timezone,
        )

        if daily_word.article_id:
            Article.objects.filter(pk=daily_word.article_id).update(
                title=WORDLY_TITLE,
                rubric=WORDLY_RUBRIC,
                lead=WORDLY_LEAD,
                body="",
                author_name="Дорогая редакция",
                status="published",
                published_at=published_at,
            )
            continue

        article = Article.objects.create(
            title=WORDLY_TITLE,
            slug=f"wordly-{daily_word.date:%Y-%m-%d}",
            rubric=WORDLY_RUBRIC,
            lead=WORDLY_LEAD,
            body="",
            author_name="Дорогая редакция",
            status="published",
            published_at=published_at,
        )
        daily_word.article_id = article.pk
        daily_word.save(update_fields=["article"])


class Migration(migrations.Migration):
    dependencies = [
        ("wordly", "0002_dailyword_article"),
    ]

    operations = [
        migrations.RunPython(publish_wordly_entries, migrations.RunPython.noop),
    ]
