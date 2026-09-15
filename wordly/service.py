from collections import Counter
from datetime import datetime, time
import re
import time as time_module

from django.core.exceptions import ValidationError
from django.db import OperationalError, transaction
from django.utils import timezone

from news.models import Article

from .models import DailyWord, WordlyGame


WORD_LENGTH = 5
MAX_ATTEMPTS = 6
RUSSIAN_LETTERS = re.compile(r"^[А-ЯЁ]{5}$")
STATE_PRIORITY = {"absent": 0, "present": 1, "correct": 2}
WORDLY_TITLE = "Редакция загадала слово"
WORDLY_RUBRIC = "Вордли"
WORDLY_LEAD = "Пять букв. Шесть попыток."
GUESS_SAVE_ATTEMPTS = 5


def normalize_letters(value: str) -> str:
    return (value or "").strip().upper().replace("Ё", "Е")


def validate_letters(value: str) -> str:
    normalized = normalize_letters(value)
    if not RUSSIAN_LETTERS.fullmatch(normalized):
        raise ValidationError("Нужно ввести ровно пять русских букв.")
    return normalized


def score_guess(answer: str, guess: str) -> list[str]:
    answer = validate_letters(answer)
    guess = validate_letters(guess)
    states = ["absent"] * WORD_LENGTH
    remaining = Counter()

    for index, (expected, actual) in enumerate(zip(answer, guess)):
        if expected == actual:
            states[index] = "correct"
        else:
            remaining[expected] += 1

    for index, actual in enumerate(guess):
        if states[index] == "correct":
            continue
        if remaining[actual] > 0:
            states[index] = "present"
            remaining[actual] -= 1

    return states


def board_rows(answer: str, guesses: list[str]) -> list[list[dict[str, str]]]:
    rows: list[list[dict[str, str]]] = []
    for guess in guesses[:MAX_ATTEMPTS]:
        states = score_guess(answer, guess)
        rows.append([
            {"letter": letter, "state": state}
            for letter, state in zip(guess, states)
        ])

    while len(rows) < MAX_ATTEMPTS:
        rows.append([{"letter": "", "state": "empty"} for _ in range(WORD_LENGTH)])
    return rows


def keyboard_states(answer: str, guesses: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for guess in guesses:
        for letter, state in zip(guess, score_guess(answer, guess)):
            previous = result.get(letter)
            if previous is None or STATE_PRIORITY[state] > STATE_PRIORITY[previous]:
                result[letter] = state
    return result


def _publication_time(target_date):
    now = timezone.now()
    if target_date == timezone.localdate(now):
        return now
    return timezone.make_aware(
        datetime.combine(target_date, time.min),
        timezone.get_current_timezone(),
    )


def _wordly_slug(target_date):
    return f"wordly-{target_date:%Y-%m-%d}"


def _is_orphaned_wordly_article(article: Article) -> bool:
    return (
        article.rubric == WORDLY_RUBRIC
        and article.title == WORDLY_TITLE
        and article.author_name == "Дорогая редакция"
    )


def _configure_publication(article: Article, daily_word: DailyWord) -> Article:
    now = timezone.now()
    if (
        article.status == Article.Status.PUBLISHED
        and article.published_at is not None
        and article.published_at <= now
    ):
        published_at = article.published_at
    else:
        published_at = _publication_time(daily_word.date)

    article.title = WORDLY_TITLE
    article.rubric = WORDLY_RUBRIC
    article.lead = WORDLY_LEAD
    article.body = ""
    article.author_name = "Дорогая редакция"
    article.status = Article.Status.PUBLISHED
    article.published_at = published_at
    article.save(
        update_fields=[
            "title",
            "rubric",
            "lead",
            "body",
            "author_name",
            "status",
            "published_at",
            "updated_at",
        ]
    )
    return article


def _ensure_publication(daily_word: DailyWord) -> Article:
    if daily_word.article_id:
        return _configure_publication(daily_word.article, daily_word)

    slug = _wordly_slug(daily_word.date)
    article = Article.objects.select_for_update().filter(slug=slug).first()
    if article is not None:
        already_linked = DailyWord.objects.filter(article=article).exclude(pk=daily_word.pk).exists()
        if already_linked or not _is_orphaned_wordly_article(article):
            raise ValidationError(
                "Служебный адрес выпуска Вордли уже занят другой публикацией. "
                "Редакции нужно проверить публикации на эту дату."
            )
    else:
        article = Article.objects.create(
            title=WORDLY_TITLE,
            slug=slug,
            rubric=WORDLY_RUBRIC,
            lead=WORDLY_LEAD,
            body="",
            author_name="Дорогая редакция",
            status=Article.Status.PUBLISHED,
            published_at=_publication_time(daily_word.date),
        )

    daily_word.article = article
    daily_word.save(update_fields=["article", "updated_at"])
    return _configure_publication(article, daily_word)


@transaction.atomic
def set_daily_word(target_date, raw_word: str) -> tuple[DailyWord, bool]:
    word = validate_letters(raw_word)
    existing = (
        DailyWord.objects.select_for_update()
        .select_related("article")
        .filter(date=target_date)
        .first()
    )
    if existing:
        publication_is_live = bool(
            existing.article_id
            and existing.article.status == Article.Status.PUBLISHED
            and existing.article.published_at is not None
            and existing.article.published_at <= timezone.now()
        )
        if existing.word != word and (existing.games.exists() or publication_is_live):
            raise ValidationError("Слово уже открыто читателям и не может быть заменено.")
        changed = existing.word != word
        if changed:
            existing.word = word
            existing.save(update_fields=["word", "updated_at"])
        _ensure_publication(existing)
        return existing, changed

    daily_word = DailyWord.objects.create(date=target_date, word=word)
    _ensure_publication(daily_word)
    return daily_word, True


def _wordly_game(user, daily_word: DailyWord) -> WordlyGame:
    for attempt in range(GUESS_SAVE_ATTEMPTS):
        try:
            game, _ = WordlyGame.objects.get_or_create(user=user, daily_word=daily_word)
            return game
        except OperationalError as exc:
            if "locked" not in str(exc).casefold() or attempt + 1 >= GUESS_SAVE_ATTEMPTS:
                raise
            time_module.sleep(0.05 * (attempt + 1))
    raise RuntimeError("Не удалось открыть партию Вордли.")


def submit_guess(user, daily_word: DailyWord, raw_guess: str) -> WordlyGame:
    """Append one attempt without losing a simultaneous attempt from the same reader.

    SQLite ignores select_for_update(), so the previous read/modify/write sequence
    could let two requests read the same guesses list and have the later save
    overwrite the earlier one. The JSON list itself is used as an optimistic
    compare-and-swap token: only the request that still sees the same list may
    update it; a loser reloads the game and appends to the new state.
    """
    guess = validate_letters(raw_guess)

    for attempt in range(GUESS_SAVE_ATTEMPTS):
        game = _wordly_game(user, daily_word)
        guesses = list(game.guesses)
        if game.won or len(guesses) >= MAX_ATTEMPTS:
            raise ValidationError("Эта партия уже завершена.")

        next_guesses = [*guesses, guess]
        won = guess == daily_word.word
        completed_at = timezone.now() if won or len(next_guesses) >= MAX_ATTEMPTS else None
        updated_at = timezone.now()

        try:
            updated = WordlyGame.objects.filter(
                pk=game.pk,
                guesses=game.guesses,
                won=False,
                completed_at__isnull=True,
            ).update(
                guesses=next_guesses,
                won=won,
                completed_at=completed_at,
                updated_at=updated_at,
            )
        except OperationalError as exc:
            if "locked" not in str(exc).casefold() or attempt + 1 >= GUESS_SAVE_ATTEMPTS:
                raise
            time_module.sleep(0.05 * (attempt + 1))
            continue

        if updated == 1:
            game.refresh_from_db(fields=["guesses", "won", "completed_at", "updated_at"])
            return game

        # Another request changed the same game between our read and write.
        # Reload and append the attempt to that newer state instead of replacing it.

    raise ValidationError("Не удалось сохранить попытку из-за одновременного запроса. Повторите еще раз.")
