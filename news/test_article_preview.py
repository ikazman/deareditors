from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Article


class ArticlePreviewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.editor = user_model.objects.create_user("editor-preview", password="secret", is_staff=True)
        self.client.force_login(self.editor)
        self.article = Article.objects.create(
            title="Старый заголовок",
            lead="Старый лид",
            body="Старый текст",
            author_name="Дорогая редакция",
        )

    def test_preview_saves_draft_then_redirects_to_get_preview(self):
        response = self.client.post(
            reverse("editor-article-edit", kwargs={"pk": self.article.pk}),
            {
                "title": "Новый заголовок",
                "lead": "Новый лид",
                "body": "Новый **текст**",
                "author_name": "Дежурный редактор",
                "action": "save_preview",
            },
        )

        self.assertRedirects(
            response,
            reverse("editor-article-preview", kwargs={"pk": self.article.pk}),
        )

        self.article.refresh_from_db()
        self.assertEqual(self.article.title, "Новый заголовок")
        self.assertEqual(self.article.lead, "Новый лид")
        self.assertEqual(self.article.body, "Новый **текст**")
        self.assertEqual(self.article.author_name, "Дежурный редактор")
        self.assertEqual(self.article.status, Article.Status.DRAFT)
        self.assertIsNone(self.article.published_at)

        preview = self.client.get(reverse("editor-article-preview", kwargs={"pk": self.article.pk}))
        self.assertEqual(preview.status_code, 200)
        self.assertContains(preview, "Предпросмотр")
        self.assertContains(preview, "Черновик сохранен")
        self.assertContains(preview, "Новый заголовок")
        self.assertContains(preview, "Новый лид")
        self.assertContains(preview, "<strong>текст</strong>", html=True)
        self.assertContains(preview, "Будем наблюдать.")
        self.assertContains(
            preview,
            reverse("editor-article-edit", kwargs={"pk": self.article.pk}),
        )
        self.assertNotContains(preview, "window.close()")

    def test_new_article_preview_creates_saved_draft(self):
        response = self.client.post(
            reverse("editor-article-create"),
            {
                "title": "Еще не материал",
                "lead": "Пока только предпросмотр",
                "body": "Редакция сначала сохраняет черновик.",
                "author_name": "Дорогая редакция",
                "action": "save_preview",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Article.objects.count(), 2)
        created = Article.objects.exclude(pk=self.article.pk).get()
        self.assertEqual(created.status, Article.Status.DRAFT)
        self.assertIsNone(created.published_at)
        self.assertEqual(
            response["Location"],
            reverse("editor-article-preview", kwargs={"pk": created.pk}),
        )

        preview = self.client.get(response["Location"])
        self.assertContains(preview, "Еще не материал")
        self.assertContains(preview, "Вернуться к редактированию")

    def test_published_article_is_not_exposed_through_draft_preview_route(self):
        published = Article.objects.create(
            title="Уже в номере",
            body="Материал опубликован.",
            status=Article.Status.PUBLISHED,
        )

        response = self.client.get(
            reverse("editor-article-preview", kwargs={"pk": published.pk})
        )

        self.assertEqual(response.status_code, 404)
