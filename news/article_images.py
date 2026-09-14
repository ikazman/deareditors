import time

from django.db import IntegrityError, OperationalError, transaction

from .models import ArticleImage


MARKER_SAVE_ATTEMPTS = 5


def save_article_image(image: ArticleImage) -> ArticleImage:
    """Save a new image, retrying the per-article marker allocation on races.

    ArticleImage has a database uniqueness constraint on (article, marker_index),
    while the legacy model allocator derives the next marker from MAX + 1.
    Concurrent uploads can therefore choose the same number. Keep the database
    constraint as the arbiter and retry with a freshly calculated marker.

    The nested atomic block is important when the caller already owns a larger
    transaction (Tarot does): a uniqueness failure rolls back only this attempt
    instead of poisoning the caller's transaction.
    """
    if not image._state.adding:
        image.save()
        return image

    for attempt in range(MARKER_SAVE_ATTEMPTS):
        image.marker_index = None
        try:
            with transaction.atomic():
                image.save()
            return image
        except IntegrityError:
            collision = ArticleImage.objects.filter(
                article_id=image.article_id,
                marker_index=image.marker_index,
            ).exists()
            if not collision or attempt + 1 >= MARKER_SAVE_ATTEMPTS:
                raise
        except OperationalError as exc:
            # Dear Editors currently runs on SQLite. A simultaneous writer can
            # surface as SQLITE_BUSY/"database is locked" instead of a unique
            # violation. Retry briefly in autocommit-sized attempts.
            if "locked" not in str(exc).casefold() or attempt + 1 >= MARKER_SAVE_ATTEMPTS:
                raise
            time.sleep(0.05 * (attempt + 1))

    raise RuntimeError("Не удалось выделить номер изображения после повторных попыток.")
