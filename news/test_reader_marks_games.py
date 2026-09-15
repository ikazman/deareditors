from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from canteen.models import DailyMenu, MenuItem, MenuSelection, MenuSelectionItem
from news.models import AchievementUnlock
from news.reader_marks import sync_reader_marks
from news.reader_marks_games import (
    CANTEEN_CAREFREE,
    CANTEEN_DISSENT,
    CANTEEN_FULL_LUNCH,
    CANTEEN_LOYAL_DISH,
    CANTEEN_POPULAR_CHOICE,
    CANTEEN_REGULAR,
    WORDLY_ARCHIVE,
    WORDLY_FIRST_TRY,
    WORDLY_LAST_LINE,
    WORDLY_VOCABULARY,
)
from wordly.models import DailyWord, WordlyGame


class ReaderGameMarksTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="reader-marks-games",
            password="secret",
        )
        self.today = timezone.localdate()

    def aware(self, day, hour=12):
        return timezone.make_aware(datetime.combine(day, time(hour=hour)))

    def create_wordly_game(self, day, *, guesses, completed_day=None):
        daily_word = DailyWord.objects.create(date=day, word="СЛОВО")
        completed_day = completed_day or day
        return WordlyGame.objects.create(
            user=self.user,
            daily_word=daily_word,
            guesses=guesses,
            won=True,
            completed_at=self.aware(completed_day),
        )

    def create_menu(self, day, specs):
        menu = DailyMenu.objects.create(menu_date=day, is_published=True)
        items = []
        for order, (category, name, price) in enumerate(specs, start=1):
            items.append(
                MenuItem.objects.create(
                    menu=menu,
                    category=category,
                    name=name,
                    price=Decimal(str(price)),
                    sort_order=order,
                )
            )
        return menu, items

    def select(self, user, menu, items):
        selection = MenuSelection.objects.create(menu=menu, user=user)
        MenuSelectionItem.objects.bulk_create(
            [MenuSelectionItem(selection=selection, item=item) for item in items]
        )
        return selection

    def mark_codes(self):
        return set(
            AchievementUnlock.objects.filter(user=self.user).values_list("code", flat=True)
        )

    def test_wordly_first_try_and_last_line(self):
        self.create_wordly_game(
            self.today - timedelta(days=2),
            guesses=["СЛОВО"],
        )
        self.create_wordly_game(
            self.today - timedelta(days=1),
            guesses=["ААААА", "БББББ", "ВВВВВ", "ГГГГГ", "ДДДДД", "СЛОВО"],
        )

        sync_reader_marks(self.user)

        codes = self.mark_codes()
        self.assertIn(WORDLY_FIRST_TRY, codes)
        self.assertIn(WORDLY_LAST_LINE, codes)

    def test_wordly_vocabulary_after_thirty_wins(self):
        for index in range(30):
            self.create_wordly_game(
                self.today - timedelta(days=40 - index),
                guesses=["СЛОВО"],
            )

        sync_reader_marks(self.user)

        self.assertIn(WORDLY_VOCABULARY, self.mark_codes())

    def test_wordly_archive_requires_thirty_days(self):
        self.create_wordly_game(
            self.today - timedelta(days=60),
            guesses=["СЛОВО"],
            completed_day=self.today - timedelta(days=30),
        )

        sync_reader_marks(self.user)

        self.assertIn(WORDLY_ARCHIVE, self.mark_codes())

    def test_canteen_personal_marks_use_closed_menus(self):
        for index in range(20):
            day = self.today - timedelta(days=25 - index)
            specs = [
                (MenuItem.Category.SECOND, "Куриный шницель", "600.00"),
            ]
            if index == 0:
                specs.extend(
                    [
                        (MenuItem.Category.FIRST, "Куриный бульон", "100.00"),
                        (MenuItem.Category.DRINK, "Компот", "100.00"),
                    ]
                )
            menu, items = self.create_menu(day, specs)
            self.select(self.user, menu, items)

        sync_reader_marks(self.user)

        codes = self.mark_codes()
        self.assertIn(CANTEEN_FULL_LUNCH, codes)
        self.assertIn(CANTEEN_REGULAR, codes)
        self.assertIn(CANTEEN_LOYAL_DISH, codes)
        self.assertIn(CANTEEN_CAREFREE, codes)

    def test_carefree_eater_is_strictly_above_ten_thousand(self):
        first_menu, first_items = self.create_menu(
            self.today - timedelta(days=3),
            [(MenuItem.Category.SECOND, "Блюдо 1", "5000.00")],
        )
        second_menu, second_items = self.create_menu(
            self.today - timedelta(days=2),
            [(MenuItem.Category.SECOND, "Блюдо 2", "5000.00")],
        )
        self.select(self.user, first_menu, first_items)
        self.select(self.user, second_menu, second_items)

        sync_reader_marks(self.user)
        self.assertNotIn(CANTEEN_CAREFREE, self.mark_codes())

        third_menu, third_items = self.create_menu(
            self.today - timedelta(days=1),
            [(MenuItem.Category.SECOND, "Блюдо 3", "0.01")],
        )
        self.select(self.user, third_menu, third_items)

        sync_reader_marks(self.user)
        self.assertIn(CANTEEN_CAREFREE, self.mark_codes())

    def test_current_menu_does_not_award_marks_before_it_closes(self):
        DailyMenu.objects.filter(menu_date=self.today).delete()
        menu, items = self.create_menu(
            self.today,
            [
                (MenuItem.Category.FIRST, "Суп", "100.00"),
                (MenuItem.Category.SECOND, "Шницель", "200.00"),
                (MenuItem.Category.DRINK, "Компот", "50.00"),
            ],
        )
        self.select(self.user, menu, items)

        sync_reader_marks(self.user)

        self.assertNotIn(CANTEEN_FULL_LUNCH, self.mark_codes())

    def test_popular_choice_and_dissent_use_completed_collective_result(self):
        others = [
            get_user_model().objects.create_user(username=f"reader-{index}")
            for index in range(4)
        ]

        dissent_menu, dissent_items = self.create_menu(
            self.today - timedelta(days=2),
            [
                (MenuItem.Category.SECOND, "Редкий выбор", "100.00"),
                (MenuItem.Category.SECOND, "Общий выбор", "100.00"),
            ],
        )
        self.select(self.user, dissent_menu, [dissent_items[0]])
        for other in others:
            self.select(other, dissent_menu, [dissent_items[1]])

        popular_menu, popular_items = self.create_menu(
            self.today - timedelta(days=1),
            [
                (MenuItem.Category.SECOND, "Победитель", "100.00"),
                (MenuItem.Category.SECOND, "Второе место", "100.00"),
            ],
        )
        self.select(self.user, popular_menu, [popular_items[0]])
        self.select(others[0], popular_menu, [popular_items[0]])
        self.select(others[1], popular_menu, [popular_items[0]])
        self.select(others[2], popular_menu, [popular_items[1]])
        self.select(others[3], popular_menu, [popular_items[1]])

        sync_reader_marks(self.user)

        codes = self.mark_codes()
        self.assertIn(CANTEEN_DISSENT, codes)
        self.assertIn(CANTEEN_POPULAR_CHOICE, codes)
