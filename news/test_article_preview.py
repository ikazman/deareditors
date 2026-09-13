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

    def test_preview_renders_unsaved_changes_without_changing_article(self):
        response = self.client.post(
            reverse("editor-article-edit", kwargs={"pk": self.article.pk}),
            {
                "title": "Новый заголовок",
                "lead": "Новый лид",
                "body": "Новый **текст**",
                "author_name": "Дежурный редактор",
                "action": "preview",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Предпросмотр")
        self.assertContains(response, "Новый заголовок")
        self.assertContains(response, "Новый лид")
        self.assertContains(response, "<strong>текст</strong>", html=True)
        self.assertContains(response, "Будем наблюдать.")

        self.article.refresh_from_db()
        self.assertEqual(self.article.title, "Старый заголовок")
        self.assertEqual(self.article.lead, "Старый лид")
        self.assertEqual(self.article.body, "Старый текст")
        self.assertEqual(self.article.status, Article.Status.DRAFT)
        self.assertIsNone(self.article.published_at)

    def test_new_article_can_be_previewed_without_creating_a_row(self):
        response = self.client.post(
            reverse("editor-article-create"),
            {
                "title": "Еще не материал",
                "lead": "Пока только предпросмотр",
                "body": "Редакция ничего не сохраняет.",
                "author_name": "Дорогая редакция",
                "action": "preview",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Еще не материал")
        self.assertEqual(Article.objects.count(), 1)
