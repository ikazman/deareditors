from datetime import time

from django.db import migrations
from django.utils import timezone


def fix_same_day_publication_time(apps, schema_editor):
    DailyWord = apps.get_model("wordly", "DailyWord")
    Article = apps.get_model("news", "Article")

    for daily_word in DailyWord.objects.select_related("article").filter(article__isnull=False).iterator():
        article = daily_word.article
        if not article.created_at or not article.published_at:
            continue

        created_local = timezone.localtime(article.created_at)
        published_local = timezone.localtime(article.published_at)
        if created_local.date() == daily_word.date and published_local.time() == time.min:
            Article.objects.filter(pk=article.pk).update(published_at=article.created_at)


class Migration(migrations.Migration):
    dependencies = [
        ("wordly", "0003_publish_wordly_entries"),
    ]

    operations = [
        migrations.RunPython(fix_same_day_publication_time, migrations.RunPython.noop),
    ]
