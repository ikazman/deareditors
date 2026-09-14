from django.db import migrations, models
from django.db.models import F, Q


def normalize_article_publication_state(apps, schema_editor):
    Article = apps.get_model("news", "Article")
    Article.objects.filter(status="draft", published_at__isnull=False).update(published_at=None)
    Article.objects.filter(status="published", published_at__isnull=True).update(
        published_at=F("created_at")
    )


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0011_achievement_snapshots"),
    ]

    operations = [
        migrations.RunPython(normalize_article_publication_state, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="article",
            constraint=models.CheckConstraint(
                condition=(
                    Q(status="draft", published_at__isnull=True)
                    | Q(status="published", published_at__isnull=False)
                ),
                name="article_status_publication_date_consistent",
            ),
        ),
    ]
