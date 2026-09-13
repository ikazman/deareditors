from django.db import migrations, models


MARK_SNAPSHOTS = {
    "correspondent_iii": (
        "Корреспондент III степени",
        "Письмо предъявителя использовано редакцией.",
    ),
    "correspondent_ii": (
        "Корреспондент II степени",
        "Использовано третье письмо предъявителя.",
    ),
    "correspondent_i": (
        "Корреспондент I степени",
        "Использовано десятое письмо предъявителя.",
    ),
    "permanent_reader": (
        "Постоянный читатель",
        "Прочитано пятьдесят материалов.",
    ),
    "anonymous_source": (
        "Источник, пожелавший остаться неизвестным",
        "Письмо предъявителя стало заметкой без раскрытия источника.",
    ),
    "complete_month": (
        "Читатель без пропусков",
        "Прочитаны все материалы, вышедшие за календарный месяц.",
    ),
    "archive_reader": (
        "Читатель архива",
        "Открыт материал старше трех месяцев.",
    ),
    "card_day_subscriber": (
        "Постоянный подписчик рубрики",
        "Прочитано тридцать выпусков рубрики «Карта дня».",
    ),
}


def backfill_snapshots(apps, schema_editor):
    AchievementUnlock = apps.get_model("news", "AchievementUnlock")
    for mark in AchievementUnlock.objects.all().iterator():
        title, description = MARK_SNAPSHOTS.get(mark.code, (mark.code, ""))
        mark.title = title
        mark.description = description
        mark.save(update_fields=["title", "description"])


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0010_reader_marks"),
    ]

    operations = [
        migrations.AddField(
            model_name="achievementunlock",
            name="title",
            field=models.CharField(default="", editable=False, max_length=160, verbose_name="название при выдаче"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="achievementunlock",
            name="description",
            field=models.TextField(default="", editable=False, verbose_name="основание при выдаче"),
            preserve_default=False,
        ),
        migrations.RunPython(backfill_snapshots, migrations.RunPython.noop),
    ]
