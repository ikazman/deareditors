from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from .models import Article, EditorialLetter, ReaderDailyVisit


class CoreScreenQueryCountTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.editor = user_model.objects.create_user(
            username="query-editor",
            password="secret-pass",
            is_staff=True,
        )
        self.reader = user_model.objects.create_user(
            username="query-reader",
            password="secret-pass",
        )

    def _count_get(self, url):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            response.content
        return len(queries)

    def _published_article(self, index):
        return Article.objects.create(
            title=f"Опубликованный материал {index}",
            body="Текст материала.",
            status=Article.Status.PUBLISHED,
        )

    def _letter_with_draft(self, index):
        article = Article.objects.create(
            title=f"Черновик из письма {index}",
            body="Текст черновика.",
        )
        return EditorialLetter.objects.create(
            body=f"Письмо в редакцию {index}",
            converted_article=article,
        )

    def test_reader_feed_queries_do_not_scale_with_article_count(self):
        ReaderDailyVisit.objects.create(user=self.reader, visit_date=timezone.localdate())
        self._published_article(0)
        self.client.force_login(self.reader)

        small_count = self._count_get(reverse("article-list"))

        for index in range(1, 26):
            self._published_article(index)

        large_count = self._count_get(reverse("article-list"))

        self.assertEqual(large_count, small_count)
        self.assertLessEqual(large_count, 5)

    def test_editor_dashboard_queries_do_not_scale_with_article_count(self):
        self._published_article(0)
        self.client.force_login(self.editor)

        small_count = self._count_get(reverse("editor-dashboard"))

        for index in range(1, 26):
            self._published_article(index)

        large_count = self._count_get(reverse("editor-dashboard"))

        self.assertEqual(large_count, small_count)
        self.assertLessEqual(large_count, 4)

    def test_editor_inbox_queries_do_not_scale_with_letter_count(self):
        self._letter_with_draft(0)
        self.client.force_login(self.editor)

        small_count = self._count_get(reverse("editor-inbox"))

        for index in range(1, 26):
            self._letter_with_draft(index)

        large_count = self._count_get(reverse("editor-inbox"))

        self.assertEqual(large_count, small_count)
        self.assertLessEqual(large_count, 4)
