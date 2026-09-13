import shutil
import tempfile
import zipfile
from datetime import date
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from openpyxl import Workbook

from .models import Article, ArticleImage, TarotCard, TarotDraw
from .tarot_service import create_card_of_day, import_tarot_bundle, question_for_date


class TarotTestMixin:
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_root = tempfile.mkdtemp(prefix="deareditors-tarot-")
        cls.media_override = override_settings(MEDIA_ROOT=cls.media_root, SECRET_KEY="test-tarot-secret")
        cls.media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.media_override.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)
        super().tearDownClass()

    def make_bundle(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(
            [
                "name",
                "description",
                "check_words",
                "prophecy",
                "meaning_straight",
                "meaning_reversed",
            ]
        )
        names = ["Влюблённые"] + [f"Карта {index}" for index in range(2, 23)]
        for index, name in enumerate(names, start=1):
            sheet.append(
                [
                    name,
                    f"Описание {index}",
                    f"слово {index}",
                    f"Прогноз {index}",
                    f"Прямое значение {index}",
                    f"Перевернутое значение {index}",
                ]
            )

        workbook_bytes = BytesIO()
        workbook.save(workbook_bytes)
        workbook.close()

        bundle_bytes = BytesIO()
        with zipfile.ZipFile(bundle_bytes, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("tarot-hb-main/high_arcane.xlsx", workbook_bytes.getvalue())
            for name in names:
                archive.writestr(
                    f"tarot-hb-main/cards/{name}.jpg",
                    b"\xff\xd8\xff\xe0test-card-image",
                )
        bundle_bytes.seek(0)
        return SimpleUploadedFile("tarot-hb.zip", bundle_bytes.getvalue(), content_type="application/zip")


class TarotServiceTests(TarotTestMixin, TestCase):
    def setUp(self):
        import_tarot_bundle(self.make_bundle())

    def test_bundle_imports_22_major_arcana_and_normalizes_yo(self):
        self.assertEqual(TarotCard.objects.count(), 22)
        self.assertTrue(TarotCard.objects.filter(name="Влюбленные").exists())
        self.assertFalse(TarotCard.objects.filter(name__contains="ё").exists())

    def test_card_of_day_creates_an_editable_article_with_image(self):
        target_date = date(2026, 9, 13)
        draw, created = create_card_of_day(target_date)

        self.assertTrue(created)
        self.assertEqual(draw.question, "Как сегодня, 13 сентября 2026 года, сложится день?")
        self.assertEqual(draw.article.rubric, "Карта дня")
        self.assertEqual(draw.article.title, draw.card_name)
        self.assertEqual(draw.article.status, Article.Status.DRAFT)
        self.assertEqual(draw.article.author_name, "Дорогая редакция")

        image = ArticleImage.objects.get(article=draw.article)
        self.assertIn(image.marker, draw.article.body)
        self.assertIn(draw.get_position_display(), draw.article.body)
        self.assertIn(draw.meaning, draw.article.body)

    def test_same_date_reuses_the_original_draw(self):
        target_date = date(2026, 9, 13)
        first, first_created = create_card_of_day(target_date)
        second, second_created = create_card_of_day(target_date)

        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(TarotDraw.objects.filter(draw_date=target_date).count(), 1)
        self.assertEqual(Article.objects.filter(rubric="Карта дня").count(), 1)

    def test_next_day_avoids_immediate_card_repeat(self):
        first, _ = create_card_of_day(date(2026, 9, 13))
        second, _ = create_card_of_day(date(2026, 9, 14))
        self.assertNotEqual(first.card_name, second.card_name)

    def test_question_uses_moscow_editorial_date_wording(self):
        self.assertEqual(
            question_for_date(date(2026, 1, 2)),
            "Как сегодня, 2 января 2026 года, сложится день?",
        )


class TarotEditorTests(TarotTestMixin, TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.editor = user_model.objects.create_user("tarot-editor", password="secret", is_staff=True)
        self.reader = user_model.objects.create_user("tarot-reader", password="secret")
        self.client.force_login(self.editor)

    def test_editor_can_import_deck_and_create_daily_draft(self):
        import_response = self.client.post(
            reverse("editor-tarot"),
            {"action": "import", "bundle": self.make_bundle()},
        )
        self.assertRedirects(import_response, reverse("editor-tarot"))
        self.assertEqual(TarotCard.objects.count(), 22)

        draw_response = self.client.post(reverse("editor-tarot"), {"action": "draw"})
        draw = TarotDraw.objects.get()
        self.assertRedirects(draw_response, reverse("editor-article-edit", kwargs={"pk": draw.article_id}))

        edit_response = self.client.get(reverse("editor-article-edit", kwargs={"pk": draw.article_id}))
        self.assertContains(edit_response, draw.card_name)
        self.assertContains(edit_response, "Посмотреть черновик")

    def test_published_tarot_article_shows_rubric_to_reader(self):
        import_tarot_bundle(self.make_bundle())
        draw, _ = create_card_of_day(date(2026, 9, 13))
        article = draw.article
        article.status = Article.Status.PUBLISHED
        article.save()

        self.client.force_login(self.reader)
        response = self.client.get(article.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<p class="article__rubric">Карта дня</p>', html=True)
