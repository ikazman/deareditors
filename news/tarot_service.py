from __future__ import annotations

import random
import zipfile
from dataclasses import dataclass
from datetime import date, timedelta
from difflib import get_close_matches
from io import BytesIO
from pathlib import PurePosixPath

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from openpyxl import load_workbook

from .models import Article, ArticleImage, TarotCard, TarotDraw


EXPECTED_MAJOR_ARCANA = 22
REQUIRED_COLUMNS = (
    "name",
    "description",
    "check_words",
    "prophecy",
    "meaning_straight",
    "meaning_reversed",
)
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


@dataclass(frozen=True)
class ImportedTarotCard:
    name: str
    description: str
    check_words: str
    prophecy: str
    meaning_straight: str
    meaning_reversed: str
    image_name: str
    image_bytes: bytes


def _editorial_text(value) -> str:
    """Keep imported source wording, but follow Dear Editors' no-yo typography."""
    if value is None:
        return ""
    return str(value).strip().replace("Ё", "Е").replace("ё", "е")


def _key(value: str) -> str:
    return " ".join(_editorial_text(value).casefold().split())


def _find_member(names: list[str], basename: str) -> str | None:
    target = basename.casefold()
    for name in names:
        if PurePosixPath(name).name.casefold() == target:
            return name
    return None


def _image_members(names: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for name in names:
        path = PurePosixPath(name)
        if path.suffix.casefold() not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue
        if "cards" not in {part.casefold() for part in path.parts[:-1]}:
            continue
        result[_key(path.stem)] = name
    return result


def _match_image(card_name: str, image_map: dict[str, str]) -> str | None:
    exact = image_map.get(_key(card_name))
    if exact:
        return exact

    # The old repository contains at least one historical filename typo.
    # A single close match is safe enough for a one-time controlled import.
    matches = get_close_matches(_key(card_name), list(image_map), n=2, cutoff=0.88)
    if len(matches) == 1:
        return image_map[matches[0]]
    return None


def _read_bundle(upload) -> list[ImportedTarotCard]:
    upload.seek(0)
    try:
        archive = zipfile.ZipFile(upload)
    except zipfile.BadZipFile:
        raise ValidationError("Не удалось открыть ZIP-архив старой колоды.") from None

    with archive:
        names = [name for name in archive.namelist() if not name.endswith("/")]
        workbook_member = _find_member(names, "high_arcane.xlsx")
        if not workbook_member:
            raise ValidationError("В архиве не найден high_arcane.xlsx.")

        image_map = _image_members(names)
        if not image_map:
            raise ValidationError("В архиве не найдена папка cards с изображениями.")

        workbook = load_workbook(BytesIO(archive.read(workbook_member)), read_only=True, data_only=True)
        sheet = workbook.active
        rows = sheet.iter_rows(values_only=True)
        try:
            header = next(rows)
        except StopIteration:
            raise ValidationError("high_arcane.xlsx пуст.") from None

        columns = {_key(value): index for index, value in enumerate(header) if value is not None}
        missing = [column for column in REQUIRED_COLUMNS if column not in columns]
        if missing:
            raise ValidationError("В high_arcane.xlsx не хватает полей: " + ", ".join(missing) + ".")

        parsed: list[ImportedTarotCard] = []
        missing_images: list[str] = []
        for row in rows:
            name = _editorial_text(row[columns["name"]])
            if not name:
                continue

            image_member = _match_image(name, image_map)
            if not image_member:
                missing_images.append(name)
                continue

            parsed.append(
                ImportedTarotCard(
                    name=name,
                    description=_editorial_text(row[columns["description"]]),
                    check_words=_editorial_text(row[columns["check_words"]]),
                    prophecy=_editorial_text(row[columns["prophecy"]]),
                    meaning_straight=_editorial_text(row[columns["meaning_straight"]]),
                    meaning_reversed=_editorial_text(row[columns["meaning_reversed"]]),
                    image_name=PurePosixPath(image_member).name,
                    image_bytes=archive.read(image_member),
                )
            )

        workbook.close()

    if missing_images:
        preview = ", ".join(missing_images[:3])
        suffix = "" if len(missing_images) <= 3 else " и другие"
        raise ValidationError(f"Не найдены изображения для карт: {preview}{suffix}.")

    if len(parsed) != EXPECTED_MAJOR_ARCANA:
        raise ValidationError(
            f"Ожидалось {EXPECTED_MAJOR_ARCANA} Старших Арканов, найдено {len(parsed)}."
        )

    return parsed


@transaction.atomic
def import_tarot_bundle(upload) -> int:
    cards = _read_bundle(upload)
    TarotCard.objects.all().delete()

    for item in cards:
        card = TarotCard(
            name=item.name,
            description=item.description,
            check_words=item.check_words,
            prophecy=item.prophecy,
            meaning_straight=item.meaning_straight,
            meaning_reversed=item.meaning_reversed,
        )
        card.image.save(item.image_name, ContentFile(item.image_bytes), save=False)
        card.save()

    return len(cards)


def question_for_date(target_date: date) -> str:
    return (
        f"Как сегодня, {target_date.day} {MONTHS_GENITIVE[target_date.month]} "
        f"{target_date.year} года, сложится день?"
    )


def _rng_for_question(question: str) -> random.Random:
    """Reproduce the old question + 0..10 noise seed without changing global RNG state."""
    seed = sum(ord(char) for char in question) + random.randint(0, 10)
    return random.Random(seed)


def _draw_card_and_position(
    cards: list[TarotCard], rng: random.Random
) -> tuple[TarotCard, str]:
    """Mirror the old Deck build: orient every card first, then draw from the full deck."""
    positioned_cards: list[tuple[TarotCard, str]] = []
    for card in cards:
        position = (
            TarotDraw.Position.REVERSED
            if rng.randint(0, 1) == 1
            else TarotDraw.Position.STRAIGHT
        )
        positioned_cards.append((card, position))

    # draw_spread(..., "one") in the original project used random.sample(deck, 1).
    # Every fresh draw uses the whole deck again; yesterday's card is not excluded.
    return rng.sample(positioned_cards, 1)[0]


def _draw_once(question: str) -> tuple[TarotCard, str, str]:
    # Import order mirrors the source workbook order used by the old Deck builder.
    cards = list(TarotCard.objects.order_by("pk"))
    if not cards:
        raise ValidationError("Сначала импортируйте колоду из tarot-hb.")

    rng = _rng_for_question(question)
    card, position = _draw_card_and_position(cards, rng)
    meaning = card.meaning_straight if position == TarotDraw.Position.STRAIGHT else card.meaning_reversed
    return card, position, meaning


def _content_type(filename: str) -> str:
    suffix = PurePosixPath(filename).suffix.casefold()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(suffix, "image/jpeg")


def _body_for_draw(image_marker: str, position_label: str, card: TarotCard, meaning: str) -> str:
    parts = [image_marker, f"**{position_label}.**"]
    if card.check_words:
        parts.append(f"*{card.check_words}*")
    parts.append(meaning)
    return "\n\n".join(parts)


def _replace_tarot_article_image_and_body(
    article: Article,
    card: TarotCard,
    position: str,
    meaning: str,
) -> None:
    article.images.all().delete()

    card.image.open("rb")
    try:
        image_bytes = card.image.read()
    finally:
        card.image.close()

    image = ArticleImage(
        article=article,
        caption="",
        alt_text=f"Карта Таро «{card.name}»",
        layout=ArticleImage.Layout.MEASURE,
        content_type=_content_type(card.image.name),
    )
    image.file.save(PurePosixPath(card.image.name).name, ContentFile(image_bytes), save=False)
    image.save()

    position_label = TarotDraw.Position(position).label
    article.body = _body_for_draw(image.marker, position_label, card, meaning)
    article.save(update_fields=["body", "updated_at"])


@transaction.atomic
def create_card_of_day(target_date: date | None = None) -> tuple[TarotDraw, bool]:
    target_date = target_date or timezone.localdate()
    existing = TarotDraw.objects.select_related("article").filter(draw_date=target_date).first()
    if existing:
        return existing, False

    question = question_for_date(target_date)
    card, position, meaning = _draw_once(question)

    article = Article.objects.create(
        title=card.name,
        rubric="Карта дня",
        lead=question,
        body="Редакция ожидает изображение карты.",
        author_name="Дорогая редакция",
        status=Article.Status.DRAFT,
    )
    _replace_tarot_article_image_and_body(article, card, position, meaning)

    draw = TarotDraw.objects.create(
        draw_date=target_date,
        question=question,
        card_name=card.name,
        position=position,
        check_words=card.check_words,
        prophecy=card.prophecy,
        meaning=meaning,
        article=article,
    )
    return draw, True


@transaction.atomic
def reroll_card_of_day(target_date: date | None = None) -> TarotDraw:
    """Collect the whole deck and run the same question through a fresh draw cycle."""
    target_date = target_date or timezone.localdate()
    draw = (
        TarotDraw.objects.select_for_update()
        .select_related("article")
        .filter(draw_date=target_date)
        .first()
    )
    if not draw:
        raise ValidationError("На эту дату еще нечего перебрасывать: сначала вытяните карту.")
    if not draw.article_id:
        raise ValidationError("У этого расклада нет редакционного черновика.")
    if draw.article.status != Article.Status.DRAFT:
        raise ValidationError("Опубликованную карту дня редакция не перебрасывает.")

    # A reroll is a new physical-style draw: same question, fresh 0..10 noise,
    # all cards back in the deck, all orientations assigned again. The result
    # is allowed to be exactly the same card and position as before.
    question = draw.question
    card, position, meaning = _draw_once(question)

    article = draw.article
    article.title = card.name
    article.slug = ""
    article.rubric = "Карта дня"
    article.lead = question
    article.body = "Редакция ожидает изображение карты."
    article.author_name = "Дорогая редакция"
    article.status = Article.Status.DRAFT
    article.save()
    _replace_tarot_article_image_and_body(article, card, position, meaning)

    draw.card_name = card.name
    draw.position = position
    draw.check_words = card.check_words
    draw.prophecy = card.prophecy
    draw.meaning = meaning
    draw.save(update_fields=["card_name", "position", "check_words", "prophecy", "meaning"])
    return draw


def recent_draws(limit: int = 7):
    return TarotDraw.objects.select_related("article").order_by("-draw_date")[:limit]
