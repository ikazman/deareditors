import json
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Article


class ReaderShellTests(TestCase):
    def setUp(self):
        self.reader = get_user_model().objects.create_user(
            username="reader-shell",
            password="reader-shell-pass",
        )
        self.editor = get_user_model().objects.create_user(
            username="editor-shell",
            password="editor-shell-pass",
            is_staff=True,
        )

    def test_publication_shows_date_but_not_publication_time(self):
        article = Article.objects.create(
            title="Время редакция оставила себе",
            body="Наблюдение продолжается.",
            status=Article.Status.PUBLISHED,
        )
        published_at = timezone.make_aware(datetime(2026, 9, 12, 20, 39))
        Article.objects.filter(pk=article.pk).update(published_at=published_at)
        self.client.force_login(self.reader)

        feed = self.client.get(reverse("article-list"))
        detail = self.client.get(article.get_absolute_url())

        self.assertContains(feed, "12.09.2026")
        self.assertContains(detail, "12.09.2026")
        self.assertNotContains(feed, "20:39")
        self.assertNotContains(detail, "20:39")

    def test_reader_navigation_is_in_header_not_colophon(self):
        self.client.force_login(self.editor)
        response = self.client.get(reverse("article-list"))
        html = response.content.decode()
        footer = html.split("<footer", 1)[1]

        self.assertIn("Письмо в редакцию", html)
        self.assertIn("Редакционный стол", html)
        self.assertIn("Выйти", html)
        self.assertNotIn("Письмо в редакцию", footer)
        self.assertNotIn("Редакционный стол", footer)
        self.assertNotIn("Выйти", footer)
        self.assertIn("Распространяется по приглашениям редакции.", footer)

    def test_login_exposes_install_manifest_and_favicon(self):
        response = self.client.get(reverse("login"))
        self.assertContains(response, "news/icons/site.webmanifest")
        self.assertContains(response, "news/favicon.svg")
        self.assertContains(response, 'name="theme-color"')

    def test_install_manifest_has_chrome_app_metadata(self):
        manifest_path = Path(settings.BASE_DIR, "static", "news", "icons", "site.webmanifest")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(manifest["name"], "Dear Editors")
        self.assertEqual(manifest["id"], "/")
        self.assertEqual(manifest["start_url"], "/")
        self.assertEqual(manifest["scope"], "/")
        self.assertEqual(manifest["display"], "standalone")
        sizes = {icon["sizes"] for icon in manifest["icons"]}
        self.assertIn("192x192", sizes)
        self.assertIn("512x512", sizes)
        self.assertTrue(any(icon.get("purpose") == "maskable" for icon in manifest["icons"]))
