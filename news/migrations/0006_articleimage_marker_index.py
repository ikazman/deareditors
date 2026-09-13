from django.db import migrations, models


def assign_marker_indexes(apps, schema_editor):
    Article = apps.get_model("news", "Article")
    ArticleImage = apps.get_model("news", "ArticleImage")

    replacements = {}
    current_article_id = None
    marker_index = 0

    for image in ArticleImage.objects.order_by("article_id", "created_at", "id"):
        if image.article_id != current_article_id:
            current_article_id = image.article_id
            marker_index = 1
        else:
            marker_index += 1

        image.marker_index = marker_index
        image.save(update_fields=["marker_index"])
        replacements.setdefault(image.article_id, []).append(
            (f"[[image:{image.pk}]]", f"[[фото {marker_index}]]")
        )

    for article_id, pairs in replacements.items():
        article = Article.objects.get(pk=article_id)
        body = article.body
        for old_marker, new_marker in pairs:
            body = body.replace(old_marker, new_marker)
        if body != article.body:
            article.body = body
            article.save(update_fields=["body"])


def restore_uuid_markers(apps, schema_editor):
    Article = apps.get_model("news", "Article")
    ArticleImage = apps.get_model("news", "ArticleImage")

    replacements = {}
    for image in ArticleImage.objects.exclude(marker_index__isnull=True):
        replacements.setdefault(image.article_id, []).append(
            (f"[[фото {image.marker_index}]]", f"[[image:{image.pk}]]")
        )

    for article_id, pairs in replacements.items():
        article = Article.objects.get(pk=article_id)
        body = article.body
        for old_marker, new_marker in pairs:
            body = body.replace(old_marker, new_marker)
        if body != article.body:
            article.body = body
            article.save(update_fields=["body"])


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0005_articleimage"),
    ]

    operations = [
        migrations.AddField(
            model_name="articleimage",
            name="marker_index",
            field=models.PositiveIntegerField(editable=False, null=True, verbose_name="номер в тексте"),
        ),
        migrations.RunPython(assign_marker_indexes, restore_uuid_markers),
        migrations.AlterField(
            model_name="articleimage",
            name="marker_index",
            field=models.PositiveIntegerField(editable=False, verbose_name="номер в тексте"),
        ),
        migrations.AddConstraint(
            model_name="articleimage",
            constraint=models.UniqueConstraint(
                fields=("article", "marker_index"),
                name="unique_article_image_marker_index",
            ),
        ),
    ]
