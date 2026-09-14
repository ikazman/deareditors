from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Article


class MobileEditorStabilizationTests(TestCase):
    def setUp(self):
        self.editor = get_user_model().objects.create_user(
            username="mobile-editor",
            password="secret-pass",
            is_staff=True,
        )
        self.article = Article.objects.create(
            title="Проверка мобильной редакции",
            body="Редакция проверяет интерфейс.",
            status=Article.Status.PUBLISHED,
        )
        self.client.force_login(self.editor)

    def test_editor_dashboard_navigation_stays_in_same_context(self):
        response = self.client.get(reverse("editor-dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'target="_blank"')
        self.assertContains(response, ">Открыть издание<")
        self.assertContains(response, ">Смотреть<")

    def test_article_editor_marks_form_for_unsaved_change_guard(self):
        response = self.client.get(reverse("editor-article-edit", args=[self.article.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-unsaved-guard')
        self.assertContains(response, 'formtarget="_blank"')

    def test_open_published_article_link_stays_in_same_context(self):
        response = self.client.get(reverse("editor-article-edit", args=[self.article.pk]))
        html = response.content.decode()

        self.assertIn(
            f'<a class="btn btn--quiet" href="{self.article.get_absolute_url()}">Открыть в издании</a>',
            html,
        )
        self.assertNotIn('Открыть в издании ↗', html)
