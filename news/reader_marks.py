import calendar
from collections import defaultdict
from datetime import datetime, time

from django.utils import timezone

from .models import AchievementUnlock, Article, EditorialLetter, ReaderArticleView
from .reader_identity import reader_fingerprint


CORRESPONDENT_RULES = (
    (AchievementUnlock.Code.CORRESPONDENT_III, 1),
    (AchievementUnlock.Code.CORRESPONDENT_II, 3),
    (AchievementUnlock.Code.CORRESPONDENT_I, 10),
)
PERMANENT_READER_THRESHOLD = 50
CARD_DAY_SUBSCRIBER_THRESHOLD = 30
CARD_DAY_RUBRIC = "Карта дня"

# Это текущие формулировки правил выдачи. При первом выполнении условия они
# копируются в AchievementUnlock и дальше не меняют уже выданную отметку.
MARK_DEFINITIONS = {
    AchievementUnlock.Code.CORRESPONDENT_III: (
        "Корреспондент III степени",
        "Письмо предъявителя использовано редакцией.",
    ),
    AchievementUnlock.Code.CORRESPONDENT_II: (
        "Корреспондент II степени",
        "Использовано третье письмо предъявителя.",
    ),
    AchievementUnlock.Code.CORRESPONDENT_I: (
        "Корреспондент I степени",
        "Использовано десятое письмо предъявителя.",
    ),
    AchievementUnlock.Code.PERMANENT_READER: (
        "Постоянный читатель",
        "Прочитано пятьдесят материалов.",
    ),
    AchievementUnlock.Code.ANONYMOUS_SOURCE: (
        "Источник, пожелавший остаться неизвестным",
        "Письмо предъявителя стало заметкой без раскрытия источника.",
    ),
    AchievementUnlock.Code.COMPLETE_MONTH: (
        "Читатель без пропусков",
        "Прочитаны все материалы, вышедшие за календарный месяц.",
    ),
    AchievementUnlock.Code.ARCHIVE_READER: (
        "Читатель архива",
        "Открыт материал старше трех месяцев.",
    ),
    AchievementUnlock.Code.CARD_DAY_SUBSCRIBER: (
        "Постоянный подписчик рубрики",
        "Прочитано тридцать выпусков рубрики «Карта дня».",
    ),
}


def _award(user, code, unlocked_at):
    title, description = MARK_DEFINITIONS[code]
    AchievementUnlock.objects.get_or_create(
        user=user,
        code=code,
        defaults={
            "title": title,
            "description": description,
            "unlocked_at": unlocked_at,
        },
    )


def _used_letters(user):
    fingerprint = reader_fingerprint(user)
    return list(
        EditorialLetter.objects.filter(
            sender_fingerprint=fingerprint,
            converted_article__status=Article.Status.PUBLISHED,
            converted_article__published_at__isnull=False,
        )
        .select_related("converted_article")
        .order_by("converted_article__published_at", "pk")
    )


def _sync_correspondent_marks(user):
    used_letters = _used_letters(user)
    for code, threshold in CORRESPONDENT_RULES:
        if len(used_letters) < threshold:
            continue
        qualifying_letter = used_letters[threshold - 1]
        _award(user, code, qualifying_letter.converted_article.published_at)

    anonymous_letter = next(
        (
            letter
            for letter in used_letters
            if not letter.sender_name.strip() or letter.anonymity_requested
        ),
        None,
    )
    if anonymous_letter is not None:
        _award(
            user,
            AchievementUnlock.Code.ANONYMOUS_SOURCE,
            anonymous_letter.converted_article.published_at,
        )


def _reader_views(user):
    return list(
        ReaderArticleView.objects.filter(user=user)
        .select_related("article")
        .order_by("first_opened_at", "pk")
    )


def _sync_volume_marks(user, views):
    if len(views) >= PERMANENT_READER_THRESHOLD:
        _award(
            user,
            AchievementUnlock.Code.PERMANENT_READER,
            views[PERMANENT_READER_THRESHOLD - 1].first_opened_at,
        )

    card_views = [view for view in views if view.article.rubric == CARD_DAY_RUBRIC]
    if len(card_views) >= CARD_DAY_SUBSCRIBER_THRESHOLD:
        _award(
            user,
            AchievementUnlock.Code.CARD_DAY_SUBSCRIBER,
            card_views[CARD_DAY_SUBSCRIBER_THRESHOLD - 1].first_opened_at,
        )


def _add_months(day, months):
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    target_day = min(day.day, calendar.monthrange(year, month)[1])
    return day.replace(year=year, month=month, day=target_day)


def _sync_archive_mark(user, views):
    qualifying = next(
        (
            view
            for view in views
            if view.article.published_at
            and timezone.localdate(view.first_opened_at)
            >= _add_months(timezone.localdate(view.article.published_at), 3)
        ),
        None,
    )
    if qualifying is not None:
        _award(
            user,
            AchievementUnlock.Code.ARCHIVE_READER,
            qualifying.first_opened_at,
        )


def _month_start(day):
    return day.replace(day=1)


def _aware_midnight(day):
    return timezone.make_aware(datetime.combine(day, time.min))


def _sync_complete_month_mark(user, views):
    today = timezone.localdate()
    current_month_start = _month_start(today)
    current_month_start_at = _aware_midnight(current_month_start)

    published = list(
        Article.objects.filter(
            status=Article.Status.PUBLISHED,
            published_at__isnull=False,
            published_at__lt=current_month_start_at,
        ).only("pk", "published_at")
    )
    by_month = defaultdict(list)
    for article in published:
        local_day = timezone.localdate(article.published_at)
        by_month[(local_day.year, local_day.month)].append(article.pk)

    views_by_article = {view.article_id: view for view in views}
    for year, month in sorted(by_month):
        article_ids = by_month[(year, month)]
        if not article_ids or not all(article_id in views_by_article for article_id in article_ids):
            continue

        latest_read_at = max(views_by_article[article_id].first_opened_at for article_id in article_ids)
        next_month_day = _add_months(datetime(year, month, 1).date(), 1)
        completed_at = _aware_midnight(next_month_day)
        _award(
            user,
            AchievementUnlock.Code.COMPLETE_MONTH,
            max(latest_read_at, completed_at),
        )
        return


def sync_reader_marks(user):
    if user.is_staff:
        return list(AchievementUnlock.objects.filter(user=user))

    _sync_correspondent_marks(user)
    views = _reader_views(user)
    _sync_volume_marks(user, views)
    _sync_archive_mark(user, views)
    _sync_complete_month_mark(user, views)
    return list(AchievementUnlock.objects.filter(user=user))
