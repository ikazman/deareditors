from .models import AchievementUnlock, Article, EditorialLetter, ReaderArticleView
from .reader_identity import reader_fingerprint


CORRESPONDENT_RULES = (
    (AchievementUnlock.Code.CORRESPONDENT_III, 1),
    (AchievementUnlock.Code.CORRESPONDENT_II, 3),
    (AchievementUnlock.Code.CORRESPONDENT_I, 10),
)
PERMANENT_READER_THRESHOLD = 50


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
        AchievementUnlock.objects.get_or_create(
            user=user,
            code=code,
            defaults={"unlocked_at": qualifying_letter.converted_article.published_at},
        )


def _sync_permanent_reader_mark(user):
    qualifying_view = (
        ReaderArticleView.objects.filter(user=user)
        .order_by("first_opened_at", "pk")
        .only("first_opened_at")[PERMANENT_READER_THRESHOLD - 1 : PERMANENT_READER_THRESHOLD]
        .first()
    )
    if qualifying_view is None:
        return

    AchievementUnlock.objects.get_or_create(
        user=user,
        code=AchievementUnlock.Code.PERMANENT_READER,
        defaults={"unlocked_at": qualifying_view.first_opened_at},
    )


def sync_reader_marks(user):
    if user.is_staff:
        return list(AchievementUnlock.objects.filter(user=user))

    _sync_correspondent_marks(user)
    _sync_permanent_reader_mark(user)
    return list(AchievementUnlock.objects.filter(user=user))
