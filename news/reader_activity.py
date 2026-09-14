from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import ReaderArticleView, ReaderDailyVisit


def should_track_reader(user) -> bool:
    return bool(user and user.is_authenticated and not user.is_staff)


def record_daily_visit(user, *, at=None):
    if not should_track_reader(user):
        return None

    moment = at or timezone.now()
    visit, _ = ReaderDailyVisit.objects.get_or_create(
        user=user,
        visit_date=timezone.localdate(moment),
    )
    return visit


def record_article_seen(user, article, *, at=None):
    """Ensure a reader/article relation exists without inflating repeat-open metrics."""
    if not should_track_reader(user):
        return None

    moment = at or timezone.now()
    record_daily_visit(user, at=moment)
    view, _ = ReaderArticleView.objects.get_or_create(
        user=user,
        article=article,
        defaults={
            "first_opened_at": moment,
            "last_opened_at": moment,
            "open_count": 1,
        },
    )
    return view


def record_article_open(user, article, *, at=None):
    if not should_track_reader(user):
        return None

    moment = at or timezone.now()
    record_daily_visit(user, at=moment)

    with transaction.atomic():
        view, created = ReaderArticleView.objects.get_or_create(
            user=user,
            article=article,
            defaults={
                "first_opened_at": moment,
                "last_opened_at": moment,
                "open_count": 1,
            },
        )
        if created:
            return view

        ReaderArticleView.objects.filter(pk=view.pk).update(
            last_opened_at=moment,
            open_count=F("open_count") + 1,
        )
        view.refresh_from_db(fields=["last_opened_at", "open_count"])
        return view
