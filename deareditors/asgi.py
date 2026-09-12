import logging
import os
import secrets
from contextlib import asynccontextmanager

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "deareditors.settings")

from django.core.asgi import get_asgi_application  # noqa: E402

django_application = get_asgi_application()

from django.conf import settings  # noqa: E402
from mcp.server.transport_security import TransportSecuritySettings  # noqa: E402
from starlette.applications import Starlette  # noqa: E402
from starlette.responses import PlainTextResponse  # noqa: E402
from starlette.routing import Mount  # noqa: E402

from .mcp_server import mcp  # noqa: E402


logger = logging.getLogger("deareditors.mcp")


def _transport_security() -> TransportSecuritySettings:
    allowed_hosts = [
        "localhost",
        "localhost:*",
        "127.0.0.1",
        "127.0.0.1:*",
    ]
    explicit_hosts: list[str] = []
    for host in settings.ALLOWED_HOSTS:
        host = (host or "").strip()
        if not host or host == "*" or host.startswith("."):
            continue
        explicit_hosts.extend([host, f"{host}:*"])
    allowed_hosts.extend(explicit_hosts)

    allowed_origins = list(settings.CSRF_TRUSTED_ORIGINS)
    configured_origins = os.environ.get("DEAR_EDITORS_MCP_ALLOWED_ORIGINS", "")
    allowed_origins.extend(item.strip() for item in configured_origins.split(",") if item.strip())
    allowed_origins.extend(
        [
            "https://perplexity.ai",
            "https://www.perplexity.ai",
        ]
    )
    allowed_origins = list(dict.fromkeys(allowed_origins))

    if "*" in settings.ALLOWED_HOSTS:
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)

    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=allowed_origins,
    )


class MCPApiKeyMiddleware:
    """Keep the editorial MCP on a credential boundary independent of reader sessions."""

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

        candidates = [api_key]
        if authorization.lower().startswith("bearer "):
            candidates.append(authorization[7:].strip())
        elif authorization:
            candidates.append(authorization)

        if not any(candidate and secrets.compare_digest(candidate, expected) for candidate in candidates):
            response = PlainTextResponse("Unauthorized", status_code=401)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


class MCPExceptionLoggingMiddleware:
    """Log transport failures without exposing credentials or internals to clients."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        try:
            await self.app(scope, receive, send)
        except Exception:
            logger.exception(
                "Unhandled Dear Editors MCP request failure: %s %s",
                scope.get("method", ""),
                scope.get("path", ""),
            )
            raise


mcp_application = mcp.streamable_http_app(
    streamable_http_path="/",
    stateless_http=True,
    json_response=True,
    host="0.0.0.0",
    transport_security=_transport_security(),
)
protected_mcp_application = MCPExceptionLoggingMiddleware(
    MCPApiKeyMiddleware(mcp_application)
)


@asynccontextmanager
async def lifespan(_app):
    print("[Dear Editors] Starting MCP session manager...", flush=True)
    async with mcp.session_manager.run():
        print("[Dear Editors] MCP session manager ready.", flush=True)
        yield
    print("[Dear Editors] MCP session manager stopped.", flush=True)


application = Starlette(
    routes=[
        Mount("/mcp", app=protected_mcp_application),
        Mount("/", app=django_application),
    ],
    lifespan=lifespan,
)
