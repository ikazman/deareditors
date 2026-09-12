from django.test import TestCase

from .editorial_service import create_draft, create_or_update_draft_from_letter, update_draft
from .models import Article, EditorialLetter


class EditorialServiceTests(TestCase):
    def test_create_draft_applies_shared_signoff_rule(self):
        article = create_draft(
            title="Редакция готовит черновик",
            body="Основной текст.\n\nБудем наблюдать.",
        )
        self.assertEqual(article.status, Article.Status.DRAFT)
        self.assertEqual(article.body, "Основной текст.")
        self.assertIsNone(article.published_at)

    def test_update_draft_refuses_published_material(self):
        article = Article.objects.create(
            title="Уже опубликовано",
            body="Текст.",
            status=Article.Status.PUBLISHED,
        )
        with self.assertRaisesMessage(ValueError, "только черновики"):
            update_draft(article, title="Попытка переписать")

    def test_letter_to_draft_keeps_source_link_and_marks_reviewed(self):
        letter = EditorialLetter.objects.create(body="На кухне исчез сахар.")
        article = create_or_update_draft_from_letter(
            letter,
            title="Редакция изучает исчезновение сахара",
            lead="Обстоятельства уточняются.",
        )
        letter.refresh_from_db()
        self.assertEqual(letter.converted_article, article)
        self.assertEqual(letter.status, EditorialLetter.Status.REVIEWED)
        self.assertIsNotNone(letter.reviewed_at)
        self.assertEqual(article.body, "На кухне исчез сахар.")
        self.assertEqual(article.status, Article.Status.DRAFT)
