from django.contrib.auth import get_user_model
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
            body="Редакция проверяет сведения.",
            status=Article.Status.PUBLISHED,
        )
        response = self.client.get(reverse("article-list"))
        self.assertContains(response, article.title)
        detail = self.client.get(article.get_absolute_url())
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Будем наблюдать.", count=1)

    def test_slug_is_generated_and_kept_unique(self):
        first = Article.objects.create(title="Очень важный слух", body="Первый")
        second = Article.objects.create(title="Очень важный слух", body="Второй")
        self.assertNotEqual(first.slug, second.slug)

    def test_draft_has_no_publication_date(self):
        article = Article.objects.create(
            title="Сначала опубликовали",
            body="А потом передумали.",
            status=Article.Status.PUBLISHED,
        )
        self.assertIsNotNone(article.published_at)
        article.status = Article.Status.DRAFT
        article.save()
        self.assertIsNone(article.published_at)


class EditorialDeskTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="editor", password="secret-pass")

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("editor-dashboard"))
        self.assertRedirects(response, f"{reverse('editor-login')}?next={reverse('editor-dashboard')}")

    def test_editor_can_create_draft(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("editor-article-create"),
            {
                "title": "Черновик из редакции",
                "lead": "Пока не публикуем.",
                "body": "Редакция проверяет сведения.",
                "author_name": "Дежурный редактор",
                "action": "draft",
            },
        )
        self.assertRedirects(response, reverse("editor-dashboard"))
        article = Article.objects.get(title="Черновик из редакции")
        self.assertEqual(article.status, Article.Status.DRAFT)
        self.assertIsNone(article.published_at)
        self.assertNotContains(self.client.get(reverse("article-list")), article.title)

    def test_editor_can_publish_article(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("editor-article-create"),
            {
                "title": "Редакция публикует материал",
                "lead": "Теперь это публично.",
                "body": "До дорогой редакции дошел слух.",
                "author_name": "Отдел наблюдений",
                "action": "publish",
            },
        )
        self.assertRedirects(response, reverse("editor-dashboard"))
        article = Article.objects.get(title="Редакция публикует материал")
        self.assertEqual(article.status, Article.Status.PUBLISHED)
        self.assertIsNotNone(article.published_at)
        self.assertContains(self.client.get(reverse("article-list")), article.title)

    def test_editor_strips_automatic_signoff_from_body(self):
        self.client.force_login(self.user)
        self.client.post(
            reverse("editor-article-create"),
            {
                "title": "Финал принадлежит редакции",
                "lead": "Редакционная политика.",
                "body": "Основной текст.\n\nБудем наблюдать.",
                "author_name": "Дорогая редакция",
                "action": "publish",
            },
        )
        article = Article.objects.get(title="Финал принадлежит редакции")
        self.assertEqual(article.body, "Основной текст.")
        detail = self.client.get(article.get_absolute_url())
        self.assertContains(detail, "Будем наблюдать.", count=1)

    def test_editor_can_unpublish_article(self):
        article = Article.objects.create(
            title="Материал снимают",
            body="Был опубликован.",
            status=Article.Status.PUBLISHED,
        )
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("editor-article-edit", args=[article.pk]),
            {
                "title": article.title,
                "lead": article.lead,
                "body": article.body,
                "author_name": article.author_name,
                "action": "draft",
            },
        )
        self.assertRedirects(response, reverse("editor-dashboard"))
        article.refresh_from_db()
        self.assertEqual(article.status, Article.Status.DRAFT)
        self.assertIsNone(article.published_at)
        self.assertNotContains(self.client.get(reverse("article-list")), article.title)
