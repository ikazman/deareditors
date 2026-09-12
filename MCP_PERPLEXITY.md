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

MCP uses dedicated revocable application keys. It does not accept Dear Editors reader sessions or editor passwords.

After deployment, open the editorial desk and go to:

```text
/editor/integrations/
```

Enter a label such as `Perplexity` and issue a new key. The full value is shown only once. Copy it directly into Perplexity before leaving the page.

Dear Editors stores only a SHA-256 digest of the full high-entropy key plus a short non-secret prefix used to identify it in the interface. Several keys can remain active at once.

For rotation without downtime:

1. issue a new key;
2. replace the key in Perplexity;
3. verify the connector works;
4. revoke the old key in Dear Editors.

The endpoint accepts a valid key as `Authorization: Bearer <key>` and also understands `X-API-Key` for compatibility with other MCP clients.

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

5. Choose **API Key** authentication and paste a key issued from `/editor/integrations/`.
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

An MCP key is an editorial credential: anyone holding it can read the editorial inbox, including sender names and contacts, and can create or edit drafts. Treat it like a password and store it only in the connector configuration.

If a key may have leaked, revoke it immediately in `/editor/integrations/` and issue another. Revocation takes effect without a deployment or application restart.

The key cannot publish a story or grant access to the newspaper. Those actions remain outside the MCP surface by design.
