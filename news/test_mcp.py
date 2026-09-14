from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from mcp import Client

from deareditors.mcp_server import _list_article_payloads, _list_inbox_payloads, mcp
from news.mcp_access import authenticate_mcp_key, issue_mcp_key
from news.models import Article, EditorialLetter, MCPAccessKey


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

    def test_read_tools_are_advertised_as_read_only(self):
        async def tools_by_name():
            async with Client(mcp) as client:
                result = await client.list_tools()
                return {tool.name: tool for tool in result.tools}

        tools = async_to_sync(tools_by_name)()
        for name in {
            "get_editorial_style",
            "list_articles",
            "get_article",
            "list_inbox",
            "get_letter",
        }:
            with self.subTest(tool=name):
                annotations = tools[name].annotations
                self.assertIsNotNone(annotations)
                self.assertTrue(annotations.read_only_hint)
                self.assertFalse(annotations.open_world_hint)

    def test_write_tools_are_advertised_as_mutations(self):
        async def tools_by_name():
            async with Client(mcp) as client:
                result = await client.list_tools()
                return {tool.name: tool for tool in result.tools}

        tools = async_to_sync(tools_by_name)()

        create_annotations = tools["create_article_draft"].annotations
        self.assertIsNotNone(create_annotations)
        self.assertFalse(create_annotations.read_only_hint)
        self.assertFalse(create_annotations.destructive_hint)
        self.assertFalse(create_annotations.idempotent_hint)
        self.assertFalse(create_annotations.open_world_hint)

        for name in {"update_article_draft", "create_draft_from_letter"}:
            with self.subTest(tool=name):
                annotations = tools[name].annotations
                self.assertIsNotNone(annotations)
                self.assertFalse(annotations.read_only_hint)
                self.assertTrue(annotations.destructive_hint)
                self.assertFalse(annotations.idempotent_hint)
                self.assertFalse(annotations.open_world_hint)

        review_annotations = tools["mark_letter_reviewed"].annotations
        self.assertIsNotNone(review_annotations)
        self.assertFalse(review_annotations.read_only_hint)
        self.assertTrue(review_annotations.destructive_hint)
        self.assertTrue(review_annotations.idempotent_hint)
        self.assertFalse(review_annotations.open_world_hint)


class MCPQueryCountTests(TestCase):
    def test_list_articles_stays_one_query_with_source_letters(self):
        first = Article.objects.create(title="Первый слух", body="Текст")
        first_letter = EditorialLetter.objects.create(body="Источник", converted_article=first)

        with CaptureQueriesContext(connection) as queries:
            payloads = _list_article_payloads(limit=50)

        self.assertEqual(len(queries), 1)
        self.assertEqual(payloads[0]["source_letter_id"], first_letter.pk)

        for index in range(20):
            article = Article.objects.create(title=f"Слух {index}", body="Текст")
            if index % 2 == 0:
                EditorialLetter.objects.create(body=f"Источник {index}", converted_article=article)

        with CaptureQueriesContext(connection) as queries:
            payloads = _list_article_payloads(limit=50)

        self.assertEqual(len(queries), 1)
        self.assertEqual(len(payloads), 21)

    def test_list_inbox_stays_one_query_with_converted_articles(self):
        first = Article.objects.create(title="Первый черновик", body="Текст")
        EditorialLetter.objects.create(body="Первое письмо", converted_article=first)

        with CaptureQueriesContext(connection) as queries:
            payloads = _list_inbox_payloads(limit=50)

        self.assertEqual(len(queries), 1)
        self.assertEqual(payloads[0]["converted_article_id"], first.pk)

        for index in range(20):
            article = Article.objects.create(title=f"Черновик {index}", body="Текст")
            EditorialLetter.objects.create(body=f"Письмо {index}", converted_article=article)

        with CaptureQueriesContext(connection) as queries:
            payloads = _list_inbox_payloads(limit=50)

        self.assertEqual(len(queries), 1)
        self.assertEqual(len(payloads), 21)


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
