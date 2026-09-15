from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .models import DailyMenu, MenuItem, MenuSelection, MenuSelectionItem
from .service import parse_menu_text


SAMPLE_MENU = """МЕНЮ

Первые блюда:
- Куриный бульон с вермишелью — 96 руб. 300 мл.
- Рассольник — 103 руб. 300 мл.

Вторые блюда:
- Куриный шницель — 164 руб. 110\\30 г.

Гарниры:
- Пюре картофельное — 79 руб. 140 г.

Напитки:
- Компот — 35 руб.
"""


class MenuParserTests(SimpleTestCase):
    def test_parser_understands_editorial_menu_format(self):
        items = parse_menu_text(SAMPLE_MENU)
        self.assertEqual(len(items), 5)
        self.assertEqual(items[0].name, "Куриный бульон с вермишелью")
        self.assertEqual(items[0].price, Decimal("96"))
        self.assertEqual(items[2].portion, "110/30 г.")
        self.assertEqual(items[-1].category, MenuItem.Category.DRINK)


class MenuViewsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.reader = User.objects.create_user(username="reader", password="pass12345")
        self.other_reader = User.objects.create_user(username="other", password="pass12345")
        self.editor = User.objects.create_user(username="editor", password="pass12345", is_staff=True)
        self.menu = DailyMenu.objects.create(menu_date=date(2030, 1, 2), is_published=True, source_text=SAMPLE_MENU)
        self.soup = MenuItem.objects.create(menu=self.menu, category=MenuItem.Category.FIRST, name="Рассольник", price=Decimal("103"), portion="300 мл.", sort_order=1)
        self.compote = MenuItem.objects.create(menu=self.menu, category=MenuItem.Category.DRINK, name="Компот", price=Decimal("35"), sort_order=2)

    def test_results_are_hidden_until_reader_submits_selection(self):
        self.client.force_login(self.reader)
        response = self.client.get(self.menu.get_absolute_url())
        self.assertContains(response, "Результаты появятся после того")

    def test_reader_can_select_multiple_items_and_change_selection(self):
        self.client.force_login(self.reader)
        response = self.client.post(self.menu.get_absolute_url(), {"items": [str(self.soup.pk), str(self.compote.pk)]})
        self.assertRedirects(response, self.menu.get_absolute_url())
        selection = MenuSelection.objects.get(menu=self.menu, user=self.reader)
        self.assertEqual(selection.selected_items.count(), 2)
        response = self.client.get(self.menu.get_absolute_url())
        self.assertContains(response, "Ваш обед:")
        self.assertContains(response, "138 ₽")
        self.client.post(self.menu.get_absolute_url(), {"items": [str(self.compote.pk)]})
        selected_item_ids = set(selection.selected_items.values_list("item_id", flat=True))
        self.assertEqual(selected_item_ids, {self.compote.pk})

    def test_aggregate_counts_include_other_readers(self):
        first = MenuSelection.objects.create(menu=self.menu, user=self.reader)
        MenuSelectionItem.objects.create(selection=first, item=self.soup)
        second = MenuSelection.objects.create(menu=self.menu, user=self.other_reader)
        MenuSelectionItem.objects.create(selection=second, item=self.soup)
        self.client.force_login(self.reader)
        response = self.client.get(self.menu.get_absolute_url())
        self.assertContains(response, "2 выбрали · 100%")

    def test_non_editor_cannot_open_menu_editor(self):
        self.client.force_login(self.reader)
        response = self.client.get(reverse("editor-menu"))
        self.assertRedirects(response, reverse("article-list"))

    def test_editor_can_import_and_publish_menu(self):
        self.client.force_login(self.editor)
        response = self.client.post(reverse("editor-menu"), {"menu_date": "2030-01-03", "source_text": SAMPLE_MENU, "action": "publish"})
        self.assertEqual(response.status_code, 302)
        menu = DailyMenu.objects.get(menu_date=date(2030, 1, 3))
        self.assertTrue(menu.is_published)
        self.assertEqual(menu.items.count(), 5)

    def test_today_menu_card_appears_in_feed(self):
        from django.utils import timezone
        DailyMenu.objects.create(menu_date=timezone.localdate(), is_published=True, source_text=SAMPLE_MENU)
        self.client.force_login(self.reader)
        response = self.client.get(reverse("article-list"))
        self.assertContains(response, "Меню столовой на сегодня")
        self.assertContains(response, "Выбрать обед")
