from datetime import timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .invite_preview import (
    INVITE_PREVIEW_ALT,
    INVITE_PREVIEW_CONTENT_TYPE,
    INVITE_PREVIEW_SIZE,
    INVITE_PREVIEW_VERSION,
    invite_reference,
    invite_series,
)
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

    def _preview_url(self):
        return reverse(
            "invite-preview",
            kwargs={
                "token": self.invitation.token,
                "version": INVITE_PREVIEW_VERSION,
            },
        )

    def _share_url(self):
        return f"{self.invitation.get_absolute_url()}?preview={INVITE_PREVIEW_VERSION}"

    def test_get_and_head_do_not_consume_invitation(self):
        url = self._share_url()

        get_response = self.client.get(url)
        head_response = self.client.head(url)

        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(head_response.status_code, 200)
        self.invitation.refresh_from_db()
        self.assertIsNone(self.invitation.accepted_at)
        self.assertIsNone(self.invitation.accepted_by)
        self.assertTrue(self.invitation.is_active)

    def test_invite_page_exposes_messenger_open_graph_metadata(self):
        response = self.client.get(self._share_url(), secure=True)
        reference = invite_reference(self.invitation)
        preview_url = self._preview_url()
        share_url = self._share_url()

        self.assertContains(response, '<meta property="og:title" content="Пригласительный билет Dear Editors">', html=True)
        self.assertContains(response, f"Билет {reference}. Действует до")
        self.assertContains(response, '<meta property="og:image:type" content="image/jpeg">', html=True)
        self.assertContains(response, '<meta property="og:image:width" content="1200">', html=True)
        self.assertContains(response, '<meta property="og:image:height" content="630">', html=True)
        self.assertContains(response, f'<meta property="og:image:alt" content="{INVITE_PREVIEW_ALT}">', html=True)
        self.assertContains(response, f'<meta property="og:image:secure_url" content="https://testserver{preview_url}">', html=True)
        self.assertContains(response, f'<meta property="og:url" content="https://testserver{share_url}">', html=True)
        self.assertContains(response, f"https://testserver{preview_url}")
        self.assertContains(response, 'name="twitter:card" content="summary_large_image"')
        self.assertNotContains(response, 'name="robots"')
        self.assertNotContains(response, "noindex")

    def test_telegram_and_whatsapp_crawlers_get_the_same_server_rendered_metadata(self):
        user_agents = (
            "TelegramBot (like TwitterBot)",
            "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
        )

        for user_agent in user_agents:
            with self.subTest(user_agent=user_agent):
                response = self.client.get(
                    self._share_url(),
                    secure=True,
                    HTTP_USER_AGENT=user_agent,
                )
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, '<meta property="og:type" content="website">', html=True)
                self.assertContains(response, f"https://testserver{self._preview_url()}")
                self.assertNotIn("Location", response.headers)

    def test_editor_shares_versioned_page_url_to_bust_messenger_page_cache(self):
        self.client.force_login(self.editor)

        response = self.client.get(reverse("editor-invitations"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"?preview={INVITE_PREVIEW_VERSION}")

    def test_invite_reference_is_short_and_series_is_separate(self):
        reference = invite_reference(self.invitation)

        self.assertRegex(reference, r"^\d{2}-\d{4}$")
        self.assertEqual(invite_series(self.invitation), "DE-I")
        self.assertNotIn("DE-I", reference)

        response = self.client.get(self.invitation.get_absolute_url())
        self.assertContains(response, "Серия DE-I")
        self.assertContains(response, reference)

    def test_invite_page_uses_nonduplicative_status(self):
        response = self.client.get(self.invitation.get_absolute_url())

        self.assertContains(response, "Не использовано")
        self.assertContains(response, "Действует до")

    def test_invite_form_does_not_autofocus_or_repeat_labels_as_placeholders(self):
        response = self.client.get(self.invitation.get_absolute_url())
        html = response.content.decode()

        self.assertNotIn("autofocus", html)
        self.assertNotIn('placeholder="Имя для входа"', html)
        self.assertNotIn('placeholder="Пароль"', html)
        self.assertContains(response, "Если не заполнить, редакция будет обращаться «предъявитель».")

    def test_invalid_invitation_status_explains_why_it_is_closed(self):
        self.invitation.revoked_at = timezone.now()
        self.invitation.save(update_fields=["revoked_at"])

        response = self.client.get(self.invitation.get_absolute_url())

        self.assertEqual(response.status_code, 410)
        self.assertContains(response, "Отозвано", status_code=410)

        self.invitation.revoked_at = None
        self.invitation.expires_at = timezone.now() - timedelta(minutes=1)
        self.invitation.save(update_fields=["revoked_at", "expires_at"])

        response = self.client.get(self.invitation.get_absolute_url())
        self.assertContains(response, "Истекло", status_code=410)

    def test_preview_is_direct_public_jpeg_with_expected_dimensions_weight_and_headers(self):
        url = self._preview_url()

        response = self.client.get(url)
        head_response = self.client.head(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(head_response.status_code, 200)
        self.assertEqual(response["Content-Type"], INVITE_PREVIEW_CONTENT_TYPE)
        self.assertEqual(head_response["Content-Type"], INVITE_PREVIEW_CONTENT_TYPE)
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertIn("max-age=31536000", response["Cache-Control"])
        self.assertNotIn("Location", response.headers)
        self.assertEqual(response["Content-Length"], str(len(response.content)))
        self.assertEqual(head_response["Content-Length"], str(len(response.content)))
        self.assertLess(len(response.content), 200 * 1024)
        self.assertTrue(response.content.startswith(b"\xff\xd8\xff"))
        image = Image.open(BytesIO(response.content))
        self.assertEqual(image.size, INVITE_PREVIEW_SIZE)
        self.assertEqual(image.format, "JPEG")

    def test_preview_version_is_in_jpeg_path_and_v4_png_urls_remain_readable(self):
        current = self.client.get(self._preview_url())
        wrong_jpeg = self.client.get(
            reverse(
                "invite-preview",
                kwargs={"token": self.invitation.token, "version": INVITE_PREVIEW_VERSION - 1},
            )
        )
        versioned_png = self.client.get(
            reverse(
                "invite-preview-png-legacy",
                kwargs={"token": self.invitation.token, "version": 4},
            )
        )
        wrong_versioned_png = self.client.get(
            reverse(
                "invite-preview-png-legacy",
                kwargs={"token": self.invitation.token, "version": INVITE_PREVIEW_VERSION},
            )
        )
        legacy_path = reverse("invite-preview-legacy", kwargs={"token": self.invitation.token})
        legacy_v3 = self.client.get(f"{legacy_path}?v=3")
        legacy_v4 = self.client.get(f"{legacy_path}?v=4")
        missing_legacy_version = self.client.get(legacy_path)

        self.assertEqual(current.status_code, 200)
        self.assertEqual(wrong_jpeg.status_code, 404)
        self.assertEqual(versioned_png.status_code, 200)
        self.assertEqual(versioned_png["Content-Type"], "image/png")
        self.assertEqual(wrong_versioned_png.status_code, 404)
        self.assertEqual(legacy_v3.status_code, 200)
        self.assertEqual(legacy_v4.status_code, 200)
        self.assertEqual(legacy_v3["Content-Type"], "image/png")
        self.assertEqual(legacy_v4["Content-Type"], "image/png")
        self.assertEqual(missing_legacy_version.status_code, 404)
