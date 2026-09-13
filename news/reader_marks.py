from .models import AchievementUnlock, Article, EditorialLetter
from .reader_identity import reader_fingerprint


CORRESPONDENT_RULES = (
    (AchievementUnlock.Code.CORRESPONDENT_III, 1),
    (AchievementUnlock.Code.CORRESPONDENT_II, 3),
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


def sync_reader_marks(user):
    if user.is_staff:
        return list(AchievementUnlock.objects.filter(user=user))

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

    return list(AchievementUnlock.objects.filter(user=user))
