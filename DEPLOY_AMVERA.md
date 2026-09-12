# Deploy Dear Editors on Amvera

Dear Editors is ready to run on Amvera with Docker and persistent SQLite storage.

## What the container does

On every start the container:

1. mounts persistent storage at `/data`;
2. runs Django migrations;
3. collects static files;
4. starts the ASGI application with Uvicorn on `0.0.0.0:$PORT`.

The ASGI application serves both the closed Dear Editors site and the authenticated editorial MCP endpoint.

In production the SQLite database lives at `/data/db.sqlite3`, so application rebuilds do not replace it.

## Amvera setup

Create a new application from the GitHub repository and let Amvera use the committed `Dockerfile` and `amvera.yaml`.

The important runtime settings are already in `amvera.yaml`:

```yaml
run:
  persistenceMount: /data
  containerPort: 8000
```

Amvera provides `PORT` for the configured container port. The entrypoint uses it automatically.

## Required environment variables

Set these in the Amvera application variables before the first production start:

```text
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=<long-random-secret>
DJANGO_ALLOWED_HOSTS=<your-amvera-hostname>
```

Generate a Django secret locally with:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

For several hostnames, use a comma-separated value:

```text
DJANGO_ALLOWED_HOSTS=project.example.amvera.io,deareditors.example.com
```

If a custom domain is added, add its HTTPS origin as well:

```text
DJANGO_CSRF_TRUSTED_ORIGINS=https://deareditors.example.com
```

## Editorial MCP

The newspaper can run without MCP. In that case `/mcp/` returns `503` and the rest of the application is unaffected.

To enable the Perplexity connector, generate a separate editorial key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

and add it to Amvera:

```text
DEAR_EDITORS_MCP_API_KEY=<generated-secret>
```

The setup steps for Perplexity and the exact MCP tool boundary are documented in [MCP_PERPLEXITY.md](MCP_PERPLEXITY.md).

## HTTPS

Secure session and CSRF cookies are enabled automatically when `DJANGO_DEBUG=0`.

After the Amvera HTTPS endpoint is confirmed to work correctly, strict HTTP-to-HTTPS redirect can be enabled with:

```text
DJANGO_SECURE_SSL_REDIRECT=1
```

It is intentionally not enabled by default so a reverse-proxy configuration mistake cannot create a redirect loop during the first launch.

## Optional runtime variables

The production defaults should be enough for Dear Editors. These variables exist only if tuning is needed later:

```text
DJANGO_DB_PATH=/data/db.sqlite3
DEAR_EDITORS_MCP_ALLOWED_ORIGINS=https://www.perplexity.ai,https://perplexity.ai
```

The container intentionally runs one Uvicorn worker. With SQLite and the expected load of Dear Editors, one process keeps writes predictable and is more than sufficient.

## First launch check

After the application starts, open:

```text
/health/
```

Expected response:

```json
{"status": "ok"}
```

The endpoint checks that Django can talk to the database, not merely that the web process is alive.

Then verify:

- `/login/` opens over HTTPS;
- an anonymous request to `/` redirects to login;
- CSS and fonts are present;
- the editor account can open `/editor/`;
- an invitation can be created and accepted by a new reader;
- an article can be created and survives an application restart.

The last check confirms that `/data` persistence is working.

If MCP is enabled, also connect Perplexity to:

```text
https://<your-host>/mcp/
```

using Streamable HTTP and the API key configured above.

## Domain

A custom domain is not required for the first launch. It is safer to deploy first on the Amvera-provided hostname, confirm persistence, authentication and MCP connectivity, and attach the final domain afterwards.
