from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from mcp import Client

from deareditors.mcp_server import mcp
from news.mcp_access import authenticate_mcp_key, issue_mcp_key
from news.models import MCPAccessKey


class MCPBootTests(SimpleTestCase):
    def test_asgi_application_mounts_mcp_and_django(self):
        from deareditors.asgi import application

        paths = [getattr(route, "path", None) for route in application.routes]
        self.assertIn("/mcp", paths)
        self.assertIn("", paths)

    def test_tool_surface_has_editorial_actions_but_no_publish(self):
        async def tool_names():
            async with Client(mcp) as client:
                result = await client.list_tools()
                return {tool.name for tool in result.tools}

        names = async_to_sync(tool_names)()
        self.assertIn("get_editorial_style", names)
        self.assertIn("create_article_draft", names)
        self.assertIn("update_article_draft", names)
        self.assertIn("create_draft_from_letter", names)
        self.assertNotIn("publish_article", names)
        self.assertFalse(any("publish" in name for name in names))


class MCPAccessKeyTests(TestCase):
    def setUp(self):
        self.editor = get_user_model().objects.create_user(
            username="mcp-editor",
            password="secret-pass",
            is_staff=True,
        )

    def test_key_is_shown_once_and_only_hash_is_stored(self):
        access_key, raw_key = issue_mcp_key(label="Perplexity", created_by=self.editor)

        self.assertTrue(raw_key.startswith(f"de_mcp_{access_key.prefix}_"))
        self.assertNotEqual(access_key.key_hash, raw_key)
        self.assertNotIn(raw_key, access_key.key_hash)
        self.assertEqual(authenticate_mcp_key(raw_key).pk, access_key.pk)

    def test_revoked_key_no_longer_authenticates(self):
        access_key, raw_key = issue_mcp_key(label="Old Perplexity", created_by=self.editor)
        access_key.revoked_at = access_key.created_at
        access_key.save(update_fields=["revoked_at"])

        self.assertIsNone(authenticate_mcp_key(raw_key))

    def test_multiple_active_keys_are_supported(self):
        first, first_raw = issue_mcp_key(label="Perplexity old", created_by=self.editor)
        second, second_raw = issue_mcp_key(label="Perplexity new", created_by=self.editor)

        self.assertEqual(authenticate_mcp_key(first_raw).pk, first.pk)
        self.assertEqual(authenticate_mcp_key(second_raw).pk, second.pk)

    def test_editor_can_issue_and_revoke_key_from_integrations_page(self):
        self.client.force_login(self.editor)
        response = self.client.post(reverse("editor-integrations"), {"label": "Perplexity"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Скопируйте сейчас")
        access_key = MCPAccessKey.objects.get(label="Perplexity")
        self.assertContains(response, access_key.masked.split("_")[2])

        response = self.client.post(reverse("editor-mcp-key-revoke", args=[access_key.pk]))
        self.assertRedirects(response, reverse("editor-integrations"))
        access_key.refresh_from_db()
        self.assertIsNotNone(access_key.revoked_at)

    def test_reader_cannot_manage_mcp_keys(self):
        reader = get_user_model().objects.create_user(username="mcp-reader", password="secret-pass")
        self.client.force_login(reader)
        response = self.client.get(reverse("editor-integrations"))
        self.assertRedirects(response, reverse("article-list"))
