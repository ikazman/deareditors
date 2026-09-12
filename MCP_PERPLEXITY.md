# Dear Editors MCP for Perplexity

Dear Editors exposes a private remote MCP endpoint for editorial work.

The connector is deliberately not an autopublisher. It can read editorial context and prepare drafts; only a human editor can publish or unpublish a material in the editorial desk.

## What the connector can do

The current MCP exposes these editorial operations:

- `get_editorial_style` — read the complete `EDITORIAL_STYLE.md`;
- `list_articles` — list recent materials, optionally only drafts or published articles;
- `get_article` — read one article or draft in full;
- `list_inbox` — list letters to the editorial office;
- `get_letter` — read one letter in full;
- `create_article_draft` — create a new draft;
- `update_article_draft` — update an existing draft;
- `create_draft_from_letter` — turn a letter into a linked draft or continue editing that draft;
- `mark_letter_reviewed` — mark a letter as reviewed.

There is intentionally no tool for publishing, unpublishing, deleting articles, managing readers, creating invitations, or changing application settings.

## Authentication

MCP uses a separate application secret. It does not accept Dear Editors reader sessions or editor passwords.

Generate a key locally:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Add the generated value to the Amvera application variables:

```text
DEAR_EDITORS_MCP_API_KEY=<generated-secret>
```

If this variable is missing, `/mcp/` returns `503` and the rest of Dear Editors continues to work normally.

The endpoint accepts the key as `Authorization: Bearer <key>` and also understands `X-API-Key` for compatibility with other MCP clients.

## Connect Perplexity

Perplexity supports custom remote MCP connectors over HTTPS with Streamable HTTP and API-key authentication.

After Dear Editors is deployed:

1. Open **Account settings → Connectors** in Perplexity.
2. Choose **+ Custom connector** and then **Remote**.
3. Name it `Dear Editors`.
4. Set the MCP Server URL to:

   ```text
   https://<your-dear-editors-host>/mcp/
   ```

5. Choose **API Key** authentication and paste the value of `DEAR_EDITORS_MCP_API_KEY`.
6. Choose **Streamable HTTP** transport.
7. Save and enable the connector.

A custom domain is not required. The Amvera HTTPS hostname is enough.

## Typical editorial workflow

A useful first request to Perplexity is:

> Прочитай редакционный стиль Dear Editors, посмотри последние пять опубликованных заметок и новые письма в редакцию. Для письма №17 предложи три заголовка и короткий проект заметки. Ничего не публикуй.

After choosing a version:

> Второй заголовок. Подготовь по нему заметку и сохрани как черновик, связанный с письмом №17.

The resulting article appears in the Dear Editors editorial desk as a normal draft. Publication still requires the editor to open it and press the publication button.

## Origin protection

The MCP transport validates host and origin as required by the protocol. By default it accepts Perplexity origins:

```text
https://www.perplexity.ai
https://perplexity.ai
```

If another MCP host needs browser-origin access, add a comma-separated override in Amvera:

```text
DEAR_EDITORS_MCP_ALLOWED_ORIGINS=https://www.perplexity.ai,https://another-host.example
```

`DJANGO_ALLOWED_HOSTS` is also used to build the MCP host allowlist, so production should continue to contain the exact Amvera/custom hostname.

## Security boundary

The MCP key is an editorial credential: anyone holding it can read the editorial inbox, including sender names and contacts, and can create or edit drafts. Treat it like a password, store it only in Amvera and the connector configuration, and rotate it if it may have leaked.

The key cannot publish a story or grant access to the newspaper. Those actions remain outside the MCP surface by design.
