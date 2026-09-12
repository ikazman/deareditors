from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Article, EditorialLetter


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

    def test_article_renders_only_editorial_markdown_subset(self):
        article = Article.objects.create(
            title="Редакция освоила форматирование",
            body=(
                "**Жирный** и *курсив*.\n\n"
                "- Первый пункт\n- Второй пункт\n\n"
                "1. Первый номер\n2. Второй номер\n\n"
                "[Нормальная ссылка](https://example.com)\n\n"
                "[Плохая ссылка](javascript:alert(1))\n\n"
                "# Это не подзаголовок\n\n"
                "<script>alert('нет')</script>"
            ),
            status=Article.Status.PUBLISHED,
        )

        html = self.client.get(article.get_absolute_url()).content.decode()
        self.assertIn("<strong>Жирный</strong>", html)
        self.assertIn("<em>курсив</em>", html)
        self.assertIn("<ul>", html)
        self.assertIn("<ol>", html)
        self.assertIn('<a href="https://example.com">Нормальная ссылка</a>', html)
        self.assertNotIn('href="javascript:', html)
        self.assertIn("# Это не подзаголовок", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>alert('нет')</script>", html)

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


class EditorialInboxTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="editor", password="secret-pass")

    def test_public_can_send_anonymous_letter(self):
        response = self.client.post(
            reverse("letter-create"),
            {"body": "В переговорной происходит что-то подозрительное.", "sender_name": "", "contact": ""},
        )
        self.assertRedirects(response, reverse("letter-sent"))
        letter = EditorialLetter.objects.get()
        self.assertEqual(letter.status, EditorialLetter.Status.NEW)
        self.assertEqual(letter.sender_name, "")
        self.assertEqual(letter.contact, "")

    def test_inbox_requires_login(self):
        response = self.client.get(reverse("editor-inbox"))
        self.assertRedirects(response, f"{reverse('editor-login')}?next={reverse('editor-inbox')}")

    def test_editor_can_mark_letter_reviewed(self):
        letter = EditorialLetter.objects.create(body="Проверить календарь.")
        self.client.force_login(self.user)
        self.client.post(reverse("editor-letter-review", args=[letter.pk]))
        letter.refresh_from_db()
        self.assertEqual(letter.status, EditorialLetter.Status.REVIEWED)
        self.assertIsNotNone(letter.reviewed_at)

    def test_editor_can_convert_letter_to_one_draft(self):
        letter = EditorialLetter.objects.create(
            body="На третьем этаже снова совещание без повестки.",
            sender_name="Источник",
            contact="source@example.test",
        )
        self.client.force_login(self.user)

        first = self.client.post(reverse("editor-letter-convert", args=[letter.pk]))
        letter.refresh_from_db()
        article = letter.converted_article

        self.assertRedirects(first, reverse("editor-article-edit", args=[article.pk]))
        self.assertEqual(article.status, Article.Status.DRAFT)
        self.assertEqual(article.body, letter.body)
        self.assertEqual(article.author_name, "Дорогая редакция")
        self.assertNotIn(letter.sender_name, article.body)
        self.assertNotIn(letter.contact, article.body)

        second = self.client.post(reverse("editor-letter-convert", args=[letter.pk]))
        self.assertRedirects(second, reverse("editor-article-edit", args=[article.pk]))
        self.assertEqual(Article.objects.count(), 1)
