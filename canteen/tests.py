from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

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

    def test_parser_normalizes_yo_to_e(self):
        items = parse_menu_text("Салаты:\n- Тёртая свёкла — 79 руб. 110 г.")
        self.assertEqual(items[0].name, "Тертая свекла")


class MenuViewsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.reader = User.objects.create_user(username="reader", password="pass12345")
        self.other_reader = User.objects.create_user(username="other", password="pass12345")
        self.editor = User.objects.create_user(username="editor", password="pass12345", is_staff=True)
        self.today = timezone.localdate()
        self.menu, _ = DailyMenu.objects.update_or_create(
            menu_date=self.today,
            defaults={"is_published": True, "source_text": SAMPLE_MENU},
        )
        self.menu.items.all().delete()
        self.menu.selections.all().delete()
        self.soup = MenuItem.objects.create(
            menu=self.menu,
            category=MenuItem.Category.FIRST,
            name="Рассольник",
            price=Decimal("103"),
            portion="300 мл.",
            sort_order=1,
        )
        self.compote = MenuItem.objects.create(
            menu=self.menu,
            category=MenuItem.Category.DRINK,
            name="Компот",
            price=Decimal("35"),
            sort_order=2,
        )

    def test_results_are_hidden_until_reader_submits_selection(self):
        self.client.force_login(self.reader)
        response = self.client.get(self.menu.get_absolute_url())
        self.assertContains(response, "Результаты появятся после того")
        self.assertNotContains(response, "menu-item--has-result")

    def test_reader_can_select_multiple_items_and_change_selection(self):
        self.client.force_login(self.reader)
        response = self.client.post(
            self.menu.get_absolute_url(),
            {"items": [str(self.soup.pk), str(self.compote.pk)]},
        )
        self.assertRedirects(response, self.menu.get_absolute_url())
        selection = MenuSelection.objects.get(menu=self.menu, user=self.reader)
        self.assertEqual(selection.selected_items.count(), 2)
        response = self.client.get(self.menu.get_absolute_url())
        self.assertContains(response, "Ваш обед:")
        self.assertContains(response, "138 ₽")
        self.client.post(self.menu.get_absolute_url(), {"items": [str(self.compote.pk)]})
        selected_item_ids = set(selection.selected_items.values_list("item_id", flat=True))
        self.assertEqual(selected_item_ids, {self.compote.pk})

    def test_ajax_save_returns_updated_results_without_redirect(self):
        self.client.force_login(self.reader)
        response = self.client.post(
            self.menu.get_absolute_url(),
            {"items": [str(self.soup.pk), str(self.compote.pk)]},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["participant_count"], 1)
        self.assertEqual(payload["selected_total"], "138.00")
        results = {item["id"]: item for item in payload["items"]}
        self.assertEqual(results[self.soup.pk]["choice_count"], 1)
        self.assertEqual(results[self.soup.pk]["choice_percent"], 100)

    def test_aggregate_counts_use_row_fill_and_hide_zero_results(self):
        first = MenuSelection.objects.create(menu=self.menu, user=self.reader)
        MenuSelectionItem.objects.create(selection=first, item=self.soup)
        second = MenuSelection.objects.create(menu=self.menu, user=self.other_reader)
        MenuSelectionItem.objects.create(selection=second, item=self.soup)
        self.client.force_login(self.reader)
        response = self.client.get(self.menu.get_absolute_url())
        self.assertContains(response, "menu-item--has-result")
        self.assertContains(response, "--share: 100%")
        self.assertNotContains(response, "0 выбрали")

    def test_menu_navigation_opens_archive(self):
        self.client.force_login(self.reader)
        response = self.client.get(reverse("menu-archive"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Архив рубрики")
        self.assertContains(response, f"Меню столовой на {self.today.day}")

    def test_archive_shows_personal_total(self):
        selection = MenuSelection.objects.create(menu=self.menu, user=self.reader)
        MenuSelectionItem.objects.create(selection=selection, item=self.soup)
        MenuSelectionItem.objects.create(selection=selection, item=self.compote)
        other = MenuSelection.objects.create(menu=self.menu, user=self.other_reader)
        MenuSelectionItem.objects.create(selection=other, item=self.soup)

        self.client.force_login(self.reader)
        response = self.client.get(reverse("menu-archive"))
        self.assertContains(response, "Ваш обед: 138 ₽")
        self.assertNotContains(response, "Выбрано ·")

    def test_public_menu_copy_does_not_use_yo(self):
        self.client.force_login(self.reader)
        detail = self.client.get(self.menu.get_absolute_url()).content.decode("utf-8")
        archive = self.client.get(reverse("menu-archive")).content.decode("utf-8")
        self.assertNotIn("ё", detail.lower())
        self.assertNotIn("ё", archive.lower())

    def test_past_menu_is_read_only_and_shows_final_results(self):
        past_menu = DailyMenu.objects.create(
            menu_date=self.today - timedelta(days=1),
            is_published=True,
            source_text=SAMPLE_MENU,
        )
        past_item = MenuItem.objects.create(
            menu=past_menu,
            category=MenuItem.Category.FIRST,
            name="Бульон",
            price=Decimal("96"),
            sort_order=1,
        )
        selection = MenuSelection.objects.create(menu=past_menu, user=self.other_reader)
        MenuSelectionItem.objects.create(selection=selection, item=past_item)
        self.client.force_login(self.reader)

        response = self.client.get(past_menu.get_absolute_url())
        self.assertContains(response, "Меню закрыто")
        self.assertContains(response, "--share: 100%")

        response = self.client.post(
            past_menu.get_absolute_url(),
            {"items": [str(past_item.pk)]},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 403)

    def test_non_editor_cannot_open_menu_editor(self):
        self.client.force_login(self.reader)
        response = self.client.get(reverse("editor-menu"))
        self.assertRedirects(response, reverse("article-list"))

    def test_editor_can_import_and_publish_menu(self):
        self.client.force_login(self.editor)
        target_date = self.today + timedelta(days=1)
        response = self.client.post(
            reverse("editor-menu"),
            {"menu_date": target_date.isoformat(), "source_text": SAMPLE_MENU, "action": "publish"},
        )
        self.assertEqual(response.status_code, 302)
        menu = DailyMenu.objects.get(menu_date=target_date)
        self.assertTrue(menu.is_published)
        self.assertEqual(menu.items.count(), 5)

    def test_editor_import_normalizes_yo_in_saved_menu(self):
        self.client.force_login(self.editor)
        target_date = self.today + timedelta(days=2)
        source_text = "Салаты:\n- Тёртая свёкла — 79 руб. 110 г."
        response = self.client.post(
            reverse("editor-menu"),
            {"menu_date": target_date.isoformat(), "source_text": source_text, "action": "publish"},
        )
        self.assertEqual(response.status_code, 302)
        menu = DailyMenu.objects.get(menu_date=target_date)
        self.assertNotIn("ё", menu.source_text.lower())
        self.assertEqual(menu.items.get().name, "Тертая свекла")

    def test_today_menu_card_appears_in_feed(self):
        self.client.force_login(self.reader)
        response = self.client.get(reverse("article-list"))
        self.assertContains(response, "Меню столовой на сегодня")
        self.assertContains(response, "Выбрать обед")
