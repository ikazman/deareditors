from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from .invite_preview import INVITE_PREVIEW_ALT, INVITE_PREVIEW_SIZE, INVITE_PREVIEW_VERSION
from .models import Invitation


class InvitePreviewTests(TestCase):
    def setUp(self):
        self.editor = get_user_model().objects.create_user(
            username="invite-editor",
            password="invite-editor-pass",
            is_staff=True,
        )
        self.invitation = Invitation.objects.create(
            label="Мария из бухгалтерии",
            created_by=self.editor,
        )

    def test_get_and_head_do_not_consume_invitation(self):
        url = self.invitation.get_absolute_url()

        get_response = self.client.get(url)
        head_response = self.client.head(url)

        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(head_response.status_code, 200)
        self.invitation.refresh_from_db()
        self.assertIsNone(self.invitation.accepted_at)
        self.assertIsNone(self.invitation.accepted_by)
        self.assertTrue(self.invitation.is_active)

    def test_invite_page_exposes_large_open_graph_preview(self):
        response = self.client.get(self.invitation.get_absolute_url(), secure=True)
        preview_url = self.client.get(
            reverse(
                "invite-preview",
                kwargs={"token": self.invitation.token, "version": INVITE_PREVIEW_VERSION},
            )
        ).request["PATH_INFO"]

        self.assertContains(response, '<meta property="og:title" content="Пригласительный билет Dear Editors">', html=True)
        self.assertContains(response, '<meta property="og:image:width" content="1200">', html=True)
        self.assertContains(response, '<meta property="og:image:height" content="630">', html=True)
        self.assertContains(response, f'<meta property="og:image:alt" content="{INVITE_PREVIEW_ALT}">', html=True)
        self.assertContains(response, f"https://testserver{preview_url}")
        self.assertContains(response, 'name="twitter:card" content="summary_large_image"')

    def test_preview_is_public_png_with_expected_dimensions(self):
        url = reverse(
            "invite-preview",
            kwargs={"token": self.invitation.token, "version": INVITE_PREVIEW_VERSION},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertIn("max-age=31536000", response["Cache-Control"])
        image = Image.open(BytesIO(response.content))
        self.assertEqual(image.size, INVITE_PREVIEW_SIZE)
        self.assertEqual(image.format, "PNG")

    def test_old_or_unknown_preview_version_is_not_served(self):
        url = reverse(
            "invite-preview",
            kwargs={"token": self.invitation.token, "version": INVITE_PREVIEW_VERSION + 1},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)
