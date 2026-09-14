from collections import Counter
from datetime import datetime, time
import re

from django.core.exceptions import ValidationError
from django.db import transaction
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
    return timezone.make_aware(
        datetime.combine(target_date, time.min),
        timezone.get_current_timezone(),
    )


def _ensure_publication(daily_word: DailyWord) -> Article:
    published_at = _publication_time(daily_word.date)

    if daily_word.article_id:
        article = daily_word.article
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

    article = Article.objects.create(
        title=WORDLY_TITLE,
        slug=f"wordly-{daily_word.date:%Y-%m-%d}",
        rubric=WORDLY_RUBRIC,
        lead=WORDLY_LEAD,
        body="",
        author_name="Дорогая редакция",
        status=Article.Status.PUBLISHED,
        published_at=published_at,
    )
    daily_word.article = article
    daily_word.save(update_fields=["article", "updated_at"])
    return article


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


@transaction.atomic
def submit_guess(user, daily_word: DailyWord, raw_guess: str) -> WordlyGame:
    guess = validate_letters(raw_guess)
    game = (
        WordlyGame.objects.select_for_update()
        .filter(user=user, daily_word=daily_word)
        .first()
    )
    if game is None:
        game = WordlyGame.objects.create(user=user, daily_word=daily_word)

    if game.won or len(game.guesses) >= MAX_ATTEMPTS:
        raise ValidationError("Эта партия уже завершена.")

    guesses = list(game.guesses)
    guesses.append(guess)
    game.guesses = guesses
    game.won = guess == daily_word.word
    if game.won or len(guesses) >= MAX_ATTEMPTS:
        game.completed_at = timezone.now()
    game.save(update_fields=["guesses", "won", "completed_at", "updated_at"])
    return game
