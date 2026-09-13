from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Article, ReaderArticleView, ReaderDailyVisit


class ReaderActivityTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.reader = user_model.objects.create_user(
            username="reader-activity",
            password="reader-activity-pass",
        )
        self.other_reader = user_model.objects.create_user(
            username="other-reader-activity",
            password="other-reader-activity-pass",
        )
        self.editor = user_model.objects.create_user(
            username="editor-activity",
            password="editor-activity-pass",
            is_staff=True,
        )
        self.article = Article.objects.create(
            title="Редакция считает читателей",
            body="Самих читателей это пока ни к чему не обязывает.",
            status=Article.Status.PUBLISHED,
        )

    def test_feed_records_one_daily_visit_for_reader(self):
        self.client.force_login(self.reader)

        self.client.get(reverse("article-list"))
        self.client.get(reverse("article-list"))

        visits = ReaderDailyVisit.objects.filter(
            user=self.reader,
            visit_date=timezone.localdate(),
        )
        self.assertEqual(visits.count(), 1)

    def test_article_open_creates_unique_view_and_counts_reopens(self):
        self.client.force_login(self.reader)

        self.client.get(self.article.get_absolute_url())
        self.client.get(self.article.get_absolute_url())
        self.client.get(self.article.get_absolute_url())

        self.assertEqual(
            ReaderArticleView.objects.filter(article=self.article).count(),
            1,
        )
        view = ReaderArticleView.objects.get(user=self.reader, article=self.article)
        self.assertEqual(view.open_count, 3)
        self.assertGreaterEqual(view.last_opened_at, view.first_opened_at)
        self.assertEqual(
            ReaderDailyVisit.objects.filter(user=self.reader).count(),
            1,
        )

    def test_different_readers_create_different_unique_views(self):
        self.client.force_login(self.reader)
        self.client.get(self.article.get_absolute_url())

        self.client.force_login(self.other_reader)
        self.client.get(self.article.get_absolute_url())

        self.assertEqual(
            ReaderArticleView.objects.filter(article=self.article).count(),
            2,
        )
        self.assertEqual(
            sum(
                ReaderArticleView.objects.filter(article=self.article).values_list(
                    "open_count", flat=True
                )
            ),
            2,
        )

    def test_staff_activity_is_not_counted(self):
        self.client.force_login(self.editor)

        self.client.get(reverse("article-list"))
        self.client.get(self.article.get_absolute_url())

        self.assertFalse(ReaderDailyVisit.objects.filter(user=self.editor).exists())
        self.assertFalse(ReaderArticleView.objects.filter(user=self.editor).exists())

    def test_missing_or_draft_article_does_not_create_activity(self):
        draft = Article.objects.create(
            title="Еще не напечатано",
            body="Редакция пока молчит.",
            status=Article.Status.DRAFT,
        )
        self.client.force_login(self.reader)

        response = self.client.get(reverse("article-detail", args=[draft.slug]))

        self.assertEqual(response.status_code, 404)
        self.assertFalse(ReaderArticleView.objects.filter(user=self.reader).exists())
        self.assertFalse(ReaderDailyVisit.objects.filter(user=self.reader).exists())

    def test_editor_dashboard_shows_unique_readers_and_total_opens(self):
        self.client.force_login(self.reader)
        self.client.get(self.article.get_absolute_url())
        self.client.get(self.article.get_absolute_url())

        self.client.force_login(self.other_reader)
        self.client.get(self.article.get_absolute_url())

        self.client.force_login(self.editor)
        response = self.client.get(reverse("editor-dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2 читателей · 3 открытий")

    def test_readership_metrics_are_not_exposed_to_readers(self):
        self.client.force_login(self.reader)
        self.client.get(self.article.get_absolute_url())
        self.client.get(self.article.get_absolute_url())

        feed = self.client.get(reverse("article-list"))
        detail = self.client.get(self.article.get_absolute_url())

        self.assertNotContains(feed, "1 читателей · 2 открытий")
        self.assertNotContains(detail, "1 читателей · 2 открытий")
