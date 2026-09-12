from django.test import SimpleTestCase


class MCPBootTests(SimpleTestCase):
    def test_asgi_application_mounts_mcp_and_django(self):
        from deareditors.asgi import application

        paths = [getattr(route, "path", None) for route in application.routes]
        self.assertIn("/mcp", paths)
        self.assertIn("", paths)
