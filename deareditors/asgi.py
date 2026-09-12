import os
import secrets
from contextlib import asynccontextmanager

from django.conf import settings
from django.core.asgi import get_asgi_application
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Mount

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "deareditors.settings")

django_application = get_asgi_application()

from .mcp_server import mcp  # noqa: E402


def _mcp_allowed_hosts() -> list[str]:
    hosts: list[str] = []
    for host in settings.ALLOWED_HOSTS:
        if host == "*":
            continue
        clean = host.lstrip(".")
        hosts.extend([clean, f"{clean}:*"])
    return hosts or ["localhost", "localhost:*", "127.0.0.1", "127.0.0.1:*"]


def _mcp_allowed_origins() -> list[str]:
    configured = os.environ.get("DEAR_EDITORS_MCP_ALLOWED_ORIGINS", "")
    origins = [item.strip() for item in configured.split(",") if item.strip()]
    if origins:
        return origins
    return ["https://www.perplexity.ai", "https://perplexity.ai"]


class MCPApiKeyMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        expected = os.environ.get("DEAR_EDITORS_MCP_API_KEY", "")
        if not expected:
            response = PlainTextResponse("MCP is not configured", status_code=503)
            await response(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        authorization = headers.get(b"authorization", b"").decode("latin-1").strip()
        api_key = headers.get(b"x-api-key", b"").decode("latin-1").strip()

        candidates = [api_key, authorization]
        if authorization.lower().startswith("bearer "):
            candidates.append(authorization[7:].strip())

        if not any(candidate and secrets.compare_digest(candidate, expected) for candidate in candidates):
            response = PlainTextResponse("Unauthorized", status_code=401)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


transport_security = TransportSecuritySettings(
    allowed_hosts=_mcp_allowed_hosts(),
    allowed_origins=_mcp_allowed_origins(),
)

mcp_application = mcp.streamable_http_app(
    streamable_http_path="/",
    stateless_http=True,
    json_response=True,
    transport_security=transport_security,
)


@asynccontextmanager
async def lifespan(app):
    async with mcp.session_manager.run():
        yield


application = Starlette(
    routes=[
        Mount("/mcp", app=MCPApiKeyMiddleware(mcp_application)),
        Mount("/", app=django_application),
    ],
    lifespan=lifespan,
)
