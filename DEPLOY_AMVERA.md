# Deploy Dear Editors on Amvera

Dear Editors is ready to run on Amvera with Docker and persistent SQLite storage.

## What the container does

On every start the container:

1. mounts persistent storage at `/data`;
2. runs Django migrations;
3. collects static files;
4. starts Gunicorn on `0.0.0.0:$PORT`.

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

Generate a secret locally with:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

For several hostnames, use a comma-separated value:

```text
DJANGO_ALLOWED_HOSTS=project.example.amvera.io,deareditors.example.com
```

If a custom domain is added, it is useful to add its HTTPS origin as well:

```text
DJANGO_CSRF_TRUSTED_ORIGINS=https://deareditors.example.com
```

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
GUNICORN_WORKERS=1
GUNICORN_THREADS=4
GUNICORN_TIMEOUT=60
```

With SQLite, one Gunicorn worker is the deliberate default. Dear Editors does not need multiple worker processes at its expected load, and this keeps writes predictable.

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

- the front page loads over HTTPS;
- CSS and fonts are present;
- `/editor/login/` opens;
- login works;
- an article can be created and survives an application restart.

The last check confirms that `/data` persistence is working.

## Domain

A custom domain is not required for the first launch. It is safer to deploy first on the Amvera-provided hostname, confirm persistence and authentication, and attach the final domain afterwards.
