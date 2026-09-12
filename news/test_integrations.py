from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class IntegrationsPageTests(TestCase):
    def setUp(self):
        self.editor = get_user_model().objects.create_user(
            username="integration-editor",
            password="integration-pass",
            is_staff=True,
        )
        self.client.force_login(self.editor)

    def test_page_shows_dynamic_mcp_connection_details(self):
        response = self.client.get(reverse("editor-integrations"), secure=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "https://testserver/mcp/")
        self.assertContains(response, "Streamable HTTP")
        self.assertContains(response, "API Key")
