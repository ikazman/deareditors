from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from news.models import Article

from .models import DailyWord
from .service import WORDLY_LEAD, WORDLY_RUBRIC, WORDLY_TITLE, set_daily_word


class WordlyPublicationRecoveryTests(TestCase):
    def setUp(self):
        self.target_date = timezone.localdate() + timedelta(days=3)
        self.slug = f"wordly-{self.target_date:%Y-%m-%d}"

    def create_orphaned_wordly_article(self):
        return Article.objects.create(
            title=WORDLY_TITLE,
            slug=self.slug,
            rubric=WORDLY_RUBRIC,
            lead=WORDLY_LEAD,
            body="",
            author_name="Дорогая редакция",
            status=Article.Status.PUBLISHED,
            published_at=timezone.now(),
        )

    def test_setting_word_reuses_orphaned_wordly_article(self):
        orphan = self.create_orphaned_wordly_article()

        daily_word, changed = set_daily_word(self.target_date, "ТОПОТ")

        self.assertTrue(changed)
        self.assertEqual(daily_word.word, "ТОПОТ")
        self.assertEqual(daily_word.article_id, orphan.pk)
        self.assertEqual(Article.objects.filter(slug=self.slug).count(), 1)

    def test_deleting_daily_word_deletes_its_feed_article(self):
        daily_word, _ = set_daily_word(self.target_date, "ТОПОТ")
        article_id = daily_word.article_id

        daily_word.delete()

        self.assertFalse(Article.objects.filter(pk=article_id).exists())

    def test_create_delete_create_again_works(self):
        first, _ = set_daily_word(self.target_date, "ТОПОТ")
        first_article_id = first.article_id
        first.delete()

        second, changed = set_daily_word(self.target_date, "ТОПОТ")

        self.assertTrue(changed)
        self.assertNotEqual(second.article_id, first_article_id)
        self.assertEqual(Article.objects.filter(slug=self.slug).count(), 1)

    def test_unrelated_article_slug_collision_is_validation_error(self):
        Article.objects.create(
            title="Обычная заметка",
            slug=self.slug,
            rubric="Новости",
            lead="",
            body="Текст",
            author_name="Редакция",
            status=Article.Status.PUBLISHED,
            published_at=timezone.now(),
        )

        with self.assertRaisesMessage(ValidationError, "Служебный адрес"):
            set_daily_word(self.target_date, "ТОПОТ")

        self.assertFalse(DailyWord.objects.filter(date=self.target_date).exists())
