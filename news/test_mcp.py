from asgiref.sync import async_to_sync
from django.test import SimpleTestCase
from mcp import Client

from deareditors.mcp_server import mcp


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
