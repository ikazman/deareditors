import re
from dataclasses import dataclass
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import DailyMenu, MenuItem


CATEGORY_ALIASES = {
    "первые блюда": MenuItem.Category.FIRST,
    "первое": MenuItem.Category.FIRST,
    "вторые блюда": MenuItem.Category.SECOND,
    "второе": MenuItem.Category.SECOND,
    "гарниры": MenuItem.Category.GARNISH,
    "гарнир": MenuItem.Category.GARNISH,
    "салаты": MenuItem.Category.SALAD,
    "салат": MenuItem.Category.SALAD,
    "напитки": MenuItem.Category.DRINK,
    "напиток": MenuItem.Category.DRINK,
}

ITEM_RE = re.compile(
    r"^(?P<name>.+?)\s*[—–-]\s*(?P<price>\d+(?:[.,]\d+)?)\s*руб\.?"
    r"(?:\s+(?P<portion>.+))?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedMenuItem:
    category: str
    name: str
    price: Decimal
    portion: str
    sort_order: int


def _normalize_yo(text):
    return text.replace("\u0451", "е").replace("\u0401", "Е")


def _clean_line(raw_line):
    line = _normalize_yo(raw_line).strip()
    if line.startswith("-"):
        line = line[1:].strip()
    line = line.replace("**", "").strip()
    return line


def parse_menu_text(source_text):
    current_category = None
    parsed = []

    for raw_line in source_text.splitlines():
        line = _clean_line(raw_line)
        if not line:
            continue
        if line.casefold().rstrip(":") == "меню":
            continue

        heading = line.rstrip(":").strip().casefold()
        if heading in CATEGORY_ALIASES:
            current_category = CATEGORY_ALIASES[heading]
            continue

        if current_category is None:
            continue

        match = ITEM_RE.match(line)
        if not match:
            raise ValidationError(f"Не удалось разобрать строку меню: «{line}»")

        portion = (match.group("portion") or "").strip().replace("\\", "/")
        parsed.append(
            ParsedMenuItem(
                category=current_category,
                name=match.group("name").strip(),
                price=Decimal(match.group("price").replace(",", ".")),
                portion=portion,
                sort_order=len(parsed) + 1,
            )
        )

    if not parsed:
        raise ValidationError("В тексте не найдено ни одной позиции меню.")
    return parsed


@transaction.atomic
def save_menu_from_text(menu_date, source_text, *, title="", lead="", publish=False):
    normalized_source = _normalize_yo(source_text).strip()
    parsed_items = parse_menu_text(normalized_source)
    menu, _ = DailyMenu.objects.select_for_update().get_or_create(menu_date=menu_date)
    menu.title = _normalize_yo(title).strip()
    menu.lead = _normalize_yo(lead).strip()
    menu.source_text = normalized_source
    if publish:
        menu.is_published = True
    menu.save()

    existing = {
        (item.category, item.name): item
        for item in menu.items.select_for_update()
    }
    keep_ids = []
    for parsed in parsed_items:
        key = (parsed.category, parsed.name)
        item = existing.get(key)
        if item is None:
            item = MenuItem(menu=menu, category=parsed.category, name=parsed.name)
        item.price = parsed.price
        item.portion = parsed.portion
        item.sort_order = parsed.sort_order
        item.save()
        keep_ids.append(item.pk)

    menu.items.exclude(pk__in=keep_ids).delete()
    return menu
