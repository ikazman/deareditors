import random
from datetime import date
from unittest.mock import call, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import Article, ArticleImage, TarotCard, TarotDraw
from .tarot_service import create_card_of_day, import_tarot_bundle, reroll_card_of_day
from .test_tarot import TarotTestMixin


class TarotRerollServiceTests(TarotTestMixin, TestCase):
    def setUp(self):
        import_tarot_bundle(self.make_bundle())

    @patch("news.tarot_service.random.randint", side_effect=[2, 9])
    def test_reroll_restarts_the_same_question_with_fresh_noise(self, randint):
        target_date = date(2026, 9, 14)
        first, _ = create_card_of_day(target_date)
        first_draw_pk = first.pk
        first_article_pk = first.article_id
        first_question = first.question
        first_image_pk = ArticleImage.objects.get(article_id=first_article_pk).pk

        rerolled = reroll_card_of_day(target_date)

        randint.assert_has_calls([call(0, 10), call(0, 10)])
        self.assertEqual(randint.call_count, 2)
        self.assertEqual(rerolled.pk, first_draw_pk)
        self.assertEqual(rerolled.article_id, first_article_pk)
        self.assertEqual(rerolled.question, first_question)

        expected_rng = random.Random(sum(ord(char) for char in first_question) + 9)
        positioned = []
        for card in TarotCard.objects.order_by("pk"):
            position = (
                TarotDraw.Position.REVERSED
                if expected_rng.randint(0, 1) == 1
                else TarotDraw.Position.STRAIGHT
            )
            positioned.append((card, position))
        expected_card, expected_position = expected_rng.sample(positioned, 1)[0]

        self.assertEqual(rerolled.card_name, expected_card.name)
        self.assertEqual(rerolled.position, expected_position)
        self.assertEqual(TarotDraw.objects.filter(draw_date=target_date).count(), 1)
        self.assertEqual(Article.objects.filter(pk=first_article_pk).count(), 1)

        replacement_image = ArticleImage.objects.get(article_id=first_article_pk)
        self.assertNotEqual(replacement_image.pk, first_image_pk)
        self.assertEqual(replacement_image.alt_text, f"Карта Таро «{expected_card.name}»")

    def test_reroll_is_allowed_to_return_exactly_the_same_card(self):
        target_date = date(2026, 9, 14)
        card = TarotCard.objects.order_by("pk").first()

        with patch(
            "news.tarot_service._draw_card_and_position",
            return_value=(card, TarotDraw.Position.STRAIGHT),
        ) as draw_card:
            first, _ = create_card_of_day(target_date)
            rerolled = reroll_card_of_day(target_date)

        self.assertEqual(draw_card.call_count, 2)
        self.assertEqual(rerolled.pk, first.pk)
        self.assertEqual(rerolled.card_name, first.card_name)
        self.assertEqual(rerolled.position, first.position)
        self.assertEqual(rerolled.card_name, card.name)
        self.assertEqual(rerolled.position, TarotDraw.Position.STRAIGHT)

    def test_reroll_replaces_manual_draft_changes_with_fresh_card_draft(self):
        target_date = date(2026, 9, 14)
        draw, _ = create_card_of_day(target_date)
        article = draw.article
        article.title = "Редактор уже что-то написал"
        article.lead = "Другой лид"
        article.body = "Другой текст"
        article.save()

        replacement_card = TarotCard.objects.order_by("pk")[1]
        with patch(
            "news.tarot_service._draw_card_and_position",
            return_value=(replacement_card, TarotDraw.Position.REVERSED),
        ):
            rerolled = reroll_card_of_day(target_date)

        article.refresh_from_db()
        self.assertEqual(article.title, replacement_card.name)
        self.assertEqual(article.lead, rerolled.question)
        self.assertIn("Положение карты: Перевернутая", article.body)
        self.assertIn(f"Ключевые слова: {replacement_card.check_words}", article.body)
        self.assertIn(
            f"Значение в выпавшем положении: {replacement_card.meaning_reversed}",
            article.body,
        )
        self.assertNotIn("Другой текст", article.body)
        self.assertEqual(article.images.count(), 1)

    def test_published_card_of_day_cannot_be_rerolled(self):
        target_date = date(2026, 9, 14)
        draw, _ = create_card_of_day(target_date)
        article = draw.article
        article.status = Article.Status.PUBLISHED
        article.save()

        with self.assertRaisesMessage(ValidationError, "Опубликованную карту дня редакция не перебрасывает."):
            reroll_card_of_day(target_date)


class TarotRerollEditorTests(TarotTestMixin, TestCase):
    def setUp(self):
        import_tarot_bundle(self.make_bundle())
        user_model = get_user_model()
        self.editor = user_model.objects.create_user(
            "tarot-reroll-editor",
            password="secret",
            is_staff=True,
        )
        self.client.force_login(self.editor)

    def test_editor_page_explains_full_deck_reroll(self):
        draw, _ = create_card_of_day()

        response = self.client.get(reverse("editor-tarot"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Перебросить карту")
        self.assertContains(response, "Новый цикл: колода собирается заново. Текущий черновик и изображения будут заменены.")
        self.assertNotContains(response, "Может выпасть та же карта")
        self.assertContains(response, reverse("editor-tarot-reroll"))
        self.assertEqual(draw.article.status, Article.Status.DRAFT)

    def test_reroll_endpoint_keeps_one_draw_and_one_article(self):
        draw, _ = create_card_of_day()
        draw_pk = draw.pk
        article_pk = draw.article_id

        response = self.client.post(reverse("editor-tarot-reroll"))

        self.assertRedirects(response, reverse("editor-article-edit", kwargs={"pk": article_pk}))
        self.assertEqual(TarotDraw.objects.count(), 1)
        self.assertEqual(Article.objects.count(), 1)
        self.assertTrue(TarotDraw.objects.filter(pk=draw_pk, article_id=article_pk).exists())

    def test_published_draw_hides_reroll_button(self):
        draw, _ = create_card_of_day()
        article = draw.article
        article.status = Article.Status.PUBLISHED
        article.save()

        response = self.client.get(reverse("editor-tarot"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Перебросить карту")
        self.assertContains(response, "Опубликованную карту дня редакция не подменяет")
