from datetime import timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .invite_preview import (
    INVITE_PREVIEW_ALT,
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
        path = reverse("invite-preview", kwargs={"token": self.invitation.token})
        return f"{path}?v={INVITE_PREVIEW_VERSION}"

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

    def test_invite_page_exposes_messenger_open_graph_metadata(self):
        response = self.client.get(self.invitation.get_absolute_url(), secure=True)
        reference = invite_reference(self.invitation)
        preview_url = self._preview_url()

        self.assertContains(response, '<meta property="og:title" content="Пригласительный билет Dear Editors">', html=True)
        self.assertContains(response, f"Билет {reference}. Действует до")
        self.assertContains(response, '<meta property="og:image:type" content="image/png">', html=True)
        self.assertContains(response, '<meta property="og:image:width" content="1200">', html=True)
        self.assertContains(response, '<meta property="og:image:height" content="630">', html=True)
        self.assertContains(response, f'<meta property="og:image:alt" content="{INVITE_PREVIEW_ALT}">', html=True)
        self.assertContains(response, f'<meta property="og:image:secure_url" content="https://testserver{preview_url}">', html=True)
        self.assertContains(response, f"https://testserver{preview_url}")
        self.assertContains(response, 'name="twitter:card" content="summary_large_image"')
        self.assertNotContains(response, 'name="robots"')
        self.assertNotContains(response, "noindex")

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

    def test_preview_is_direct_public_png_with_expected_dimensions_and_weight(self):
        url = self._preview_url()

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertIn("max-age=31536000", response["Cache-Control"])
        self.assertLess(len(response.content), 500 * 1024)
        image = Image.open(BytesIO(response.content))
        self.assertEqual(image.size, INVITE_PREVIEW_SIZE)
        self.assertEqual(image.format, "PNG")

    def test_preview_version_is_query_parameter_and_required(self):
        path = reverse("invite-preview", kwargs={"token": self.invitation.token})

        missing = self.client.get(path)
        old = self.client.get(f"{path}?v={INVITE_PREVIEW_VERSION - 1}")
        current = self.client.get(f"{path}?v={INVITE_PREVIEW_VERSION}")

        self.assertEqual(missing.status_code, 404)
        self.assertEqual(old.status_code, 404)
        self.assertEqual(current.status_code, 200)
        self.assertEqual(current.redirect_chain if hasattr(current, "redirect_chain") else [], [])
