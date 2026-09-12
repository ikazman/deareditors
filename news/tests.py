from django.test import TestCase
from django.urls import reverse

from .models import Article


class PublishingTests(TestCase):
    def test_draft_is_not_visible_in_feed(self):
        Article.objects.create(title="Секретный черновик", body="Пока никому.")
        response = self.client.get(reverse("article-list"))
        self.assertNotContains(response, "Секретный черновик")

    def test_published_article_is_visible_and_has_detail_page(self):
        article = Article.objects.create(
            title="До редакции дошел слух",
            lead="Кажется, что-то происходит.",
            body="Будем наблюдать.",
            status=Article.Status.PUBLISHED,
        )
        response = self.client.get(reverse("article-list"))
        self.assertContains(response, article.title)
        detail = self.client.get(article.get_absolute_url())
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Будем наблюдать.")

    def test_slug_is_generated_and_kept_unique(self):
        first = Article.objects.create(title="Очень важный слух", body="Первый")
        second = Article.objects.create(title="Очень важный слух", body="Второй")
        self.assertNotEqual(first.slug, second.slug)
