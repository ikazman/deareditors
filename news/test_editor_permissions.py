from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from news.mcp_access import issue_mcp_key
from news.models import Article, ArticleImage, EditorialLetter, Invitation, TarotDraw
from wordly.models import DailyWord
from wordly.service import WORDLY_LEAD, WORDLY_TITLE, set_daily_word


class DestructiveEndpointMethodTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.editor = user_model.objects.create_user(
            "method-editor",
            password="secret",
            is_staff=True,
        )
        self.invitation = Invitation.objects.create(label="Method invite", created_by=self.editor)
        self.access_key, _ = issue_mcp_key(label="Method MCP", created_by=self.editor)
        self.letter = EditorialLetter.objects.create(body="Ничего не произошло.")
        self.article = Article.objects.create(title="Черновик", body="Текст")
        self.client.force_login(self.editor)

    def test_destructive_endpoints_reject_get_without_changing_state(self):
        urls = [
            reverse("editor-invitation-revoke", args=[self.invitation.pk]),
            reverse("editor-mcp-key-revoke", args=[self.access_key.pk]),
            reverse("editor-letter-review", args=[self.letter.pk]),
            reverse("editor-letter-convert", args=[self.letter.pk]),
            reverse("editor-tarot-reroll"),
            reverse("editor-article-image-upload", args=[self.article.pk]),
            reverse("logout"),
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 405)

        self.invitation.refresh_from_db()
        self.access_key.refresh_from_db()
        self.letter.refresh_from_db()
        self.assertIsNone(self.invitation.revoked_at)
        self.assertIsNone(self.access_key.revoked_at)
        self.assertEqual(self.letter.status, EditorialLetter.Status.NEW)
        self.assertIsNone(self.letter.converted_article_id)
        self.assertEqual(ArticleImage.objects.count(), 0)

        # GET /logout/ must not silently log the editor out.
        self.assertEqual(self.client.get(reverse("editor-dashboard")).status_code, 200)


class EditorPermissionBoundaryTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.editor = user_model.objects.create_user(
            "permission-editor",
            password="secret",
            is_staff=True,
        )
        self.reader = user_model.objects.create_user(
            "permission-reader",
            password="secret",
        )
        self.invitation = Invitation.objects.create(label="Private invite", created_by=self.editor)
        self.access_key, _ = issue_mcp_key(label="Private MCP", created_by=self.editor)
        self.letter = EditorialLetter.objects.create(body="Только редакции.")
        self.article = Article.objects.create(title="Редакторский черновик", body="Исходный текст")
        self.client.force_login(self.reader)

    def assert_reader_redirected(self, response):
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("article-list"))

    def test_reader_cannot_call_editor_mutations_by_direct_url(self):
        responses = [
            self.client.post(reverse("editor-invitation-revoke", args=[self.invitation.pk])),
            self.client.post(reverse("editor-mcp-key-revoke", args=[self.access_key.pk])),
            self.client.post(reverse("editor-letter-review", args=[self.letter.pk])),
            self.client.post(reverse("editor-letter-convert", args=[self.letter.pk])),
            self.client.post(reverse("editor-tarot-reroll")),
            self.client.post(reverse("editor-invitations"), {"label": "Чужое приглашение"}),
            self.client.post(reverse("editor-integrations"), {"label": "Чужой MCP"}),
            self.client.post(reverse("editor-tarot"), {"action": "draw"}),
            self.client.post(
                reverse("editor-article-edit", args=[self.article.pk]),
                {
                    "title": "Подменено",
                    "lead": "",
                    "body": "Подменено",
                    "author_name": "Не редакция",
                    "action": "publish",
                },
            ),
            self.client.post(
                reverse("editor-article-create"),
                {
                    "title": "Чужой материал",
                    "lead": "",
                    "body": "Чужой текст",
                    "author_name": "Не редакция",
                    "action": "publish",
                },
            ),
            self.client.post(
                reverse("editor-wordly"),
                {"date": timezone.localdate().isoformat(), "word": "СЛУХИ"},
            ),
        ]

        for response in responses:
            self.assert_reader_redirected(response)

        self.invitation.refresh_from_db()
        self.access_key.refresh_from_db()
        self.letter.refresh_from_db()
        self.article.refresh_from_db()
        self.assertIsNone(self.invitation.revoked_at)
        self.assertIsNone(self.access_key.revoked_at)
        self.assertEqual(self.letter.status, EditorialLetter.Status.NEW)
        self.assertIsNone(self.letter.converted_article_id)
        self.assertEqual(self.article.title, "Редакторский черновик")
        self.assertEqual(self.article.status, Article.Status.DRAFT)
        self.assertFalse(Article.objects.filter(title="Чужой материал").exists())
        self.assertFalse(Invitation.objects.filter(label="Чужое приглашение").exists())
        self.assertFalse(DailyWord.objects.exists())
        self.assertFalse(TarotDraw.objects.exists())


class GeneratedWordlyArticleProtectionTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.editor = user_model.objects.create_user(
            "wordly-guard-editor",
            password="secret",
            is_staff=True,
        )
        self.target_date = timezone.localdate() + timedelta(days=1)
        self.daily_word, _ = set_daily_word(self.target_date, "СЛУХИ")
        self.article = self.daily_word.article
        self.client.force_login(self.editor)

    def test_generic_editor_does_not_open_generated_wordly_article(self):
        response = self.client.get(reverse("editor-article-edit", args=[self.article.pk]))

        self.assertRedirects(response, reverse("editor-wordly"))

    def test_generic_editor_cannot_unpublish_or_rewrite_wordly_article(self):
        response = self.client.post(
            reverse("editor-article-edit", args=[self.article.pk]),
            {
                "title": "Случайно переписали Вордли",
                "lead": "Другой лид",
                "body": "Другой текст",
                "author_name": "Другой автор",
                "action": "draft",
            },
        )

        self.assertRedirects(response, reverse("editor-wordly"))
        self.article.refresh_from_db()
        self.assertEqual(self.article.title, WORDLY_TITLE)
        self.assertEqual(self.article.lead, WORDLY_LEAD)
        self.assertEqual(self.article.body, "")
        self.assertEqual(self.article.status, Article.Status.PUBLISHED)
        self.assertIsNotNone(self.article.published_at)

    def test_generic_image_upload_is_rejected_for_wordly_article(self):
        response = self.client.post(
            reverse("editor-article-image-upload", args=[self.article.pk]),
            {},
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(ArticleImage.objects.filter(article=self.article).count(), 0)

    def test_regular_article_still_uses_generic_editor(self):
        regular = Article.objects.create(title="Обычный черновик", body="До редакции дошел слух.")

        response = self.client.post(
            reverse("editor-article-edit", args=[regular.pk]),
            {
                "title": "Обычная публикация",
                "lead": "Лид",
                "body": "Обычный текст",
                "author_name": "Дорогая редакция",
                "action": "publish",
            },
        )

        self.assertRedirects(response, reverse("editor-dashboard"))
        regular.refresh_from_db()
        self.assertEqual(regular.title, "Обычная публикация")
        self.assertEqual(regular.status, Article.Status.PUBLISHED)
        self.assertIsNotNone(regular.published_at)
