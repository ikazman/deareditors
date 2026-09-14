from pathlib import Path

from asgiref.sync import sync_to_async
from django.conf import settings
from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from news.editorial_service import (
    create_draft,
    create_or_update_draft_from_letter,
    mark_letter_reviewed as review_letter,
    update_draft,
)
from news.models import Article, EditorialLetter


# Keep the client-visible safety contract aligned with the proven inabD MCP
# implementation. Read tools are explicitly safe, closed-world and idempotent;
# additive writes are non-destructive. Mutations of existing editorial state are
# marked separately rather than weakening the read contract.
READ_ONLY = ToolAnnotations(
    read_only_hint=True,
    idempotent_hint=True,
    open_world_hint=False,
)
WRITE_ADDITIVE = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=False,
    open_world_hint=False,
)
WRITE_MUTATING = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=False,
    open_world_hint=False,
)
WRITE_IDEMPOTENT_MUTATING = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=True,
    open_world_hint=False,
)


mcp = MCPServer(
    "Dear Editors",
    instructions=(
        "Dear Editors is a closed editorial publication. Read the editorial guide before preparing "
        "or revising copy. Read existing articles and inbox letters whenever needed for context. "
        "You may create and revise drafts, but you must never publish, unpublish or delete articles, "
        "or manage reader access through this connector."
    ),
)


def _db(function):
    return sync_to_async(function, thread_sensitive=True)


def _style_text() -> str:
    return Path(settings.BASE_DIR, "EDITORIAL_STYLE.md").read_text(encoding="utf-8")


def _article_payload(article: Article) -> dict:
    return {
        "id": article.pk,
        "title": article.title,
        "slug": article.slug,
        "lead": article.lead,
        "body": article.body,
        "author_name": article.author_name,
        "status": article.status,
        "created_at": article.created_at.isoformat(),
        "updated_at": article.updated_at.isoformat(),
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "source_letter_id": getattr(article, "source_letter", None).pk if hasattr(article, "source_letter") else None,
    }


def _letter_payload(letter: EditorialLetter) -> dict:
    return {
        "id": letter.pk,
        "body": letter.body,
        "sender_name": letter.sender_name,
        "contact": letter.contact,
        "anonymity_requested": letter.anonymity_requested,
        "status": letter.status,
        "created_at": letter.created_at.isoformat(),
        "reviewed_at": letter.reviewed_at.isoformat() if letter.reviewed_at else None,
        "converted_article_id": letter.converted_article_id,
    }


def _list_article_payloads(status: str = "all", limit: int = 20) -> list[dict]:
    if status not in {"all", Article.Status.DRAFT, Article.Status.PUBLISHED}:
        raise ValueError("status должен быть all, draft или published")
    limit = max(1, min(limit, 50))
    queryset = Article.objects.select_related("source_letter")
    if status != "all":
        queryset = queryset.filter(status=status)
    return [_article_payload(article) for article in queryset[:limit]]


def _list_inbox_payloads(status: str = "all", limit: int = 20) -> list[dict]:
    if status not in {"all", EditorialLetter.Status.NEW, EditorialLetter.Status.REVIEWED}:
        raise ValueError("status должен быть all, new или reviewed")
    limit = max(1, min(limit, 50))
    queryset = EditorialLetter.objects.select_related("converted_article")
    if status != "all":
        queryset = queryset.filter(status=status)
    return [_letter_payload(letter) for letter in queryset[:limit]]


@mcp.resource("editorial-style://guide")
def editorial_style_resource() -> str:
    """Full Dear Editors editorial guide."""
    return _style_text()


@mcp.tool(title="Read Dear Editors editorial guide", annotations=READ_ONLY)
async def get_editorial_style() -> str:
    """Read the full Dear Editors editorial guide before preparing or revising copy."""
    return await sync_to_async(_style_text, thread_sensitive=False)()


@mcp.tool(title="List Dear Editors articles", annotations=READ_ONLY)
async def list_articles(status: str = "all", limit: int = 20) -> list[dict]:
    """List recent articles. status is all, draft or published; limit is clamped to 1-50."""
    return await _db(lambda: _list_article_payloads(status=status, limit=limit))()


@mcp.tool(title="Get Dear Editors article", annotations=READ_ONLY)
async def get_article(article_id: int) -> dict:
    """Get one article or draft by ID."""
    def load():
        try:
            article = Article.objects.select_related("source_letter").get(pk=article_id)
        except Article.DoesNotExist as exc:
            raise ValueError("Материал не найден") from exc
        return _article_payload(article)

    return await _db(load)()


@mcp.tool(title="List Dear Editors inbox", annotations=READ_ONLY)
async def list_inbox(status: str = "all", limit: int = 20) -> list[dict]:
    """List recent editorial inbox letters. status is all, new or reviewed; limit is clamped to 1-50."""
    return await _db(lambda: _list_inbox_payloads(status=status, limit=limit))()


@mcp.tool(title="Get Dear Editors letter", annotations=READ_ONLY)
async def get_letter(letter_id: int) -> dict:
    """Get one editorial inbox letter by ID."""
    def load():
        try:
            letter = EditorialLetter.objects.select_related("converted_article").get(pk=letter_id)
        except EditorialLetter.DoesNotExist as exc:
            raise ValueError("Письмо не найдено") from exc
        return _letter_payload(letter)

    return await _db(load)()


@mcp.tool(title="Create Dear Editors draft", annotations=WRITE_ADDITIVE)
async def create_article_draft(
    title: str,
    body: str,
    lead: str = "",
    author_name: str = "Дорогая редакция",
) -> dict:
    """Create a new draft article. This tool never publishes the article."""
    def create():
        article = create_draft(title=title, lead=lead, body=body, author_name=author_name)
        return _article_payload(article)

    return await _db(create)()


@mcp.tool(title="Update Dear Editors draft", annotations=WRITE_MUTATING)
async def update_article_draft(
    article_id: int,
    title: str | None = None,
    lead: str | None = None,
    body: str | None = None,
    author_name: str | None = None,
) -> dict:
    """Revise an existing draft. Published articles cannot be changed through MCP."""
    def update():
        try:
            article = Article.objects.get(pk=article_id)
        except Article.DoesNotExist as exc:
            raise ValueError("Материал не найден") from exc
        article = update_draft(
            article,
            title=title,
            lead=lead,
            body=body,
            author_name=author_name,
        )
        return _article_payload(article)

    return await _db(update)()


@mcp.tool(title="Create draft from Dear Editors letter", annotations=WRITE_MUTATING)
async def create_draft_from_letter(
    letter_id: int,
    title: str | None = None,
    lead: str | None = None,
    body: str | None = None,
    author_name: str = "Дорогая редакция",
) -> dict:
    """Create or revise a draft from an inbox letter while preserving the source link."""
    def create_or_update():
        try:
            letter = EditorialLetter.objects.get(pk=letter_id)
        except EditorialLetter.DoesNotExist as exc:
            raise ValueError("Письмо не найдено") from exc
        article = create_or_update_draft_from_letter(
            letter,
            title=title,
            lead=lead,
            body=body,
            author_name=author_name,
        )
        return _article_payload(article)

    return await _db(create_or_update)()


@mcp.tool(title="Mark Dear Editors letter reviewed", annotations=WRITE_IDEMPOTENT_MUTATING)
async def mark_letter_reviewed(letter_id: int) -> dict:
    """Mark one inbox letter as reviewed without creating an article."""
    def mark_reviewed():
        try:
            letter = EditorialLetter.objects.get(pk=letter_id)
        except EditorialLetter.DoesNotExist as exc:
            raise ValueError("Письмо не найдено") from exc
        review_letter(letter)
        return _letter_payload(letter)

    return await _db(mark_reviewed)()
