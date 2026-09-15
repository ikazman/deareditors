from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import EditorialLetter


class EditorMailNotificationTests(TestCase):
    def setUp(self):
        self.editor = get_user_model().objects.create_user(
            username="editor-mail",
            password="editor-mail-pass",
            is_staff=True,
        )
        self.client.force_login(self.editor)

    def test_mail_status_counts_only_new_letters_and_exposes_no_letter_content(self):
        EditorialLetter.objects.create(body="already reviewed", status=EditorialLetter.Status.REVIEWED)
        EditorialLetter.objects.create(body="first secret letter")
        latest = EditorialLetter.objects.create(body="second secret letter")

        response = self.client.get(reverse("editor-mail-status"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "new_count": 2,
                "latest_id": latest.pk,
            },
        )
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertNotContains(response, "secret")

    def test_editor_shell_wires_mail_badge_and_notification_opt_in(self):
        response = self.client.get(reverse("editor-dashboard"))

        self.assertContains(response, 'data-editor-mail-link')
        self.assertContains(response, f'data-status-url="{reverse("editor-mail-status")}"')
        self.assertContains(response, 'data-editor-mail-count')
        self.assertContains(response, 'data-mail-notification-toggle')
        self.assertContains(response, "news/editor-mail.css")
        self.assertContains(response, "news/editor-mail.js")

    def test_mail_status_is_editor_only(self):
        reader = get_user_model().objects.create_user(
            username="reader-mail",
            password="reader-mail-pass",
        )
        self.client.force_login(reader)

        response = self.client.get(reverse("editor-mail-status"))

        self.assertRedirects(response, reverse("article-list"))
