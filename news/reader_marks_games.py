from collections import Counter, defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count
from django.utils import timezone

from .models import AchievementUnlock


WORDLY_FIRST_TRY = "wordly_first_try"
WORDLY_LAST_LINE = "wordly_last_line"
WORDLY_VOCABULARY = "wordly_vocabulary"
WORDLY_ARCHIVE = "wordly_archive"
CANTEEN_FULL_LUNCH = "canteen_full_lunch"
CANTEEN_REGULAR = "canteen_regular"
CANTEEN_LOYAL_DISH = "canteen_loyal_dish"
CANTEEN_POPULAR_CHOICE = "canteen_popular_choice"
CANTEEN_DISSENT = "canteen_dissent"
CANTEEN_CAREFREE = "canteen_carefree"

WORDLY_VOCABULARY_THRESHOLD = 30
CANTEEN_REGULAR_THRESHOLD = 20
CANTEEN_LOYAL_DISH_THRESHOLD = 5
CANTEEN_DISSENT_MIN_PARTICIPANTS = 5
CANTEEN_CAREFREE_THRESHOLD = Decimal("10000")


MARK_DEFINITIONS = {
    WORDLY_FIRST_TRY: (
        "Слово с первого раза",
        "Слово дня угадано с первой попытки.",
    ),
    WORDLY_LAST_LINE: (
        "Шестая строка",
        "Слово найдено на шестой и последней попытке.",
    ),
    WORDLY_VOCABULARY: (
        "Словарный запас",
        "Угадано тридцать слов дня.",
    ),
    WORDLY_ARCHIVE: (
        "Архив слов",
        "Разгадано слово из архива.",
    ),
    CANTEEN_FULL_LUNCH: (
        "Первое, второе и компот",
        "В одном меню выбраны первое, второе и напиток.",
    ),
    CANTEEN_REGULAR: (
        "Постоянный посетитель",
        "Выбор сделан в двадцати выпусках «Меню дня».",
    ),
    CANTEEN_LOYAL_DISH: (
        "Верность блюду",
        "Одно и то же блюдо выбрано пять раз.",
    ),
    CANTEEN_POPULAR_CHOICE: (
        "Народный выбор",
        "Выбор предъявителя совпал с выбором большинства.",
    ),
    CANTEEN_DISSENT: (
        "Особое мнение",
        "Выбрано блюдо, которое в тот день больше не выбрал никто.",
    ),
    CANTEEN_CAREFREE: (
        "Беспечный едок",
        "Общая стоимость выбранных блюд превысила 10 000 рублей.",
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


def _aware_midnight(day):
    return timezone.make_aware(datetime.combine(day, time.min))


def _menu_completed_at(menu_date):
    return _aware_midnight(menu_date + timedelta(days=1))


def _sync_wordly_marks(user):
    from wordly.models import WordlyGame

    games = list(
        WordlyGame.objects.filter(
            user=user,
            won=True,
            completed_at__isnull=False,
        )
        .select_related("daily_word")
        .order_by("completed_at", "pk")
    )
    if not games:
        return

    first_try = next((game for game in games if len(game.guesses) == 1), None)
    if first_try is not None:
        _award(user, WORDLY_FIRST_TRY, first_try.completed_at)

    last_line = next((game for game in games if len(game.guesses) == 6), None)
    if last_line is not None:
        _award(user, WORDLY_LAST_LINE, last_line.completed_at)

    if len(games) >= WORDLY_VOCABULARY_THRESHOLD:
        _award(
            user,
            WORDLY_VOCABULARY,
            games[WORDLY_VOCABULARY_THRESHOLD - 1].completed_at,
        )

    archive_game = next(
        (
            game
            for game in games
            if timezone.localdate(game.completed_at)
            >= game.daily_word.date + timedelta(days=30)
        ),
        None,
    )
    if archive_game is not None:
        _award(user, WORDLY_ARCHIVE, archive_game.completed_at)


def _closed_canteen_selections(user):
    from canteen.models import MenuSelection

    today = timezone.localdate()
    selections = (
        MenuSelection.objects.filter(
            user=user,
            menu__menu_date__lt=today,
        )
        .select_related("menu")
        .prefetch_related("selected_items__item")
        .order_by("menu__menu_date", "pk")
    )
    result = []
    for selection in selections:
        items = [link.item for link in selection.selected_items.all()]
        if items:
            result.append((selection, items))
    return result


def _sync_canteen_personal_marks(user, entries):
    from canteen.models import MenuItem

    full_lunch = next(
        (
            selection
            for selection, items in entries
            if {
                MenuItem.Category.FIRST,
                MenuItem.Category.SECOND,
                MenuItem.Category.DRINK,
            }.issubset({item.category for item in items})
        ),
        None,
    )
    if full_lunch is not None:
        _award(
            user,
            CANTEEN_FULL_LUNCH,
            _menu_completed_at(full_lunch.menu.menu_date),
        )

    if len(entries) >= CANTEEN_REGULAR_THRESHOLD:
        selection = entries[CANTEEN_REGULAR_THRESHOLD - 1][0]
        _award(
            user,
            CANTEEN_REGULAR,
            _menu_completed_at(selection.menu.menu_date),
        )

    dish_counts = Counter()
    loyal_at = None
    for selection, items in entries:
        names = {item.name.strip().casefold() for item in items if item.name.strip()}
        for name in names:
            dish_counts[name] += 1
            if dish_counts[name] == CANTEEN_LOYAL_DISH_THRESHOLD and loyal_at is None:
                loyal_at = _menu_completed_at(selection.menu.menu_date)
    if loyal_at is not None:
        _award(user, CANTEEN_LOYAL_DISH, loyal_at)

    spent = Decimal("0")
    carefree_at = None
    for selection, items in entries:
        spent += sum((item.price for item in items), Decimal("0"))
        if spent > CANTEEN_CAREFREE_THRESHOLD:
            carefree_at = _menu_completed_at(selection.menu.menu_date)
            break
    if carefree_at is not None:
        _award(user, CANTEEN_CAREFREE, carefree_at)


def _sync_canteen_collective_marks(user, entries):
    from canteen.models import MenuSelection, MenuSelectionItem

    if not entries:
        return

    menu_ids = [selection.menu_id for selection, _items in entries]
    participant_counts = {
        row["menu_id"]: row["total"]
        for row in (
            MenuSelection.objects.filter(
                menu_id__in=menu_ids,
                selected_items__isnull=False,
            )
            .values("menu_id")
            .annotate(total=Count("id", distinct=True))
        )
    }

    choice_counts = defaultdict(dict)
    for row in (
        MenuSelectionItem.objects.filter(selection__menu_id__in=menu_ids)
        .values("selection__menu_id", "item_id")
        .annotate(total=Count("id"))
    ):
        choice_counts[row["selection__menu_id"]][row["item_id"]] = row["total"]

    popular_at = None
    dissent_at = None

    for selection, items in entries:
        menu_id = selection.menu_id
        counts = choice_counts.get(menu_id, {})
        participant_count = participant_counts.get(menu_id, 0)
        if not counts:
            continue

        if popular_at is None and participant_count >= 2:
            highest = max(counts.values())
            if any(counts.get(item.pk, 0) == highest for item in items):
                popular_at = _menu_completed_at(selection.menu.menu_date)

        if dissent_at is None and participant_count >= CANTEEN_DISSENT_MIN_PARTICIPANTS:
            if any(counts.get(item.pk, 0) == 1 for item in items):
                dissent_at = _menu_completed_at(selection.menu.menu_date)

        if popular_at is not None and dissent_at is not None:
            break

    if popular_at is not None:
        _award(user, CANTEEN_POPULAR_CHOICE, popular_at)
    if dissent_at is not None:
        _award(user, CANTEEN_DISSENT, dissent_at)


def sync_game_marks(user):
    if user.is_staff:
        return

    _sync_wordly_marks(user)
    entries = _closed_canteen_selections(user)
    _sync_canteen_personal_marks(user, entries)
    _sync_canteen_collective_marks(user, entries)
