import secrets

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import ReaderArticleView, ReaderProfile


TICKET_ATTEMPTS = 32
MONTHS_GENITIVE = (
    "",
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)


def _new_ticket_number():
    return f"DE-{secrets.randbelow(100):02d}-{secrets.randbelow(10000):04d}"


def get_or_create_reader_profile(user):
    existing = ReaderProfile.objects.filter(user=user).first()
    if existing is not None:
        return existing

    for _ in range(TICKET_ATTEMPTS):
        try:
            with transaction.atomic():
                return ReaderProfile.objects.create(
                    user=user,
                    ticket_number=_new_ticket_number(),
                )
        except IntegrityError:
            existing = ReaderProfile.objects.filter(user=user).first()
            if existing is not None:
                return existing

    raise RuntimeError("Не удалось выдать уникальный номер читательского билета.")


def reader_stats(user, profile):
    issued_date = timezone.localdate(profile.issued_at)
    today = timezone.localdate()
    return {
        "articles_read": ReaderArticleView.objects.filter(user=user).count(),
        "days_with_publication": max((today - issued_date).days, 0),
        "issued_today": issued_date == today,
        "reader_since_label": f"Читатель с {MONTHS_GENITIVE[issued_date.month]} {issued_date.year}",
    }
