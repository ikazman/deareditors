from pathlib import Path

from django.conf import settings
from django.utils import timezone
from mcp.server import MCPServer

from news.editorial_service import create_draft, create_or_update_draft_from_letter, update_draft
from news.models import Article, EditorialLetter


mcp = MCPServer(
    "Dear Editors",
    instructions=(
        "Редакционный коннектор Dear Editors. Перед подготовкой текста прочитайте редакционный стиль. "
        "Коннектор может читать публикации и почту редакции, создавать и исправлять черновики. "
        "Он не умеет публиковать, снимать с публикации, удалять материалы или управлять доступом."
    ),
)


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
        "status": letter.status,
        "created_at": letter.created_at.isoformat(),
        "reviewed_at": letter.reviewed_at.isoformat() if letter.reviewed_at else None,
        "converted_article_id": letter.converted_article_id,
    }


@mcp.resource("editorial-style://guide")
def editorial_style_resource() -> str:
    """Полный редакционный гайд Dear Editors."""
    return _style_text()


@mcp.tool()
def get_editorial_style() -> str:
    """Прочитать полный редакционный гайд Dear Editors перед подготовкой или правкой заметки."""
    return _style_text()


@mcp.tool()
def list_articles(status: str = "all", limit: int = 20) -> list[dict]:
    """Получить последние материалы. status: all, draft или published; limit от 1 до 50."""
    if status not in {"all", Article.Status.DRAFT, Article.Status.PUBLISHED}:
        raise ValueError("status должен быть all, draft или published")
    limit = max(1, min(limit, 50))
    queryset = Article.objects.all()
    if status != "all":
        queryset = queryset.filter(status=status)
    return [_article_payload(article) for article in queryset[:limit]]


@mcp.tool()
def get_article(article_id: int) -> dict:
    """Получить конкретный материал или черновик по ID целиком."""
    try:
        article = Article.objects.get(pk=article_id)
    except Article.DoesNotExist as exc:
        raise ValueError("Материал не найден") from exc
    return _article_payload(article)


@mcp.tool()
def list_inbox(status: str = "all", limit: int = 20) -> list[dict]:
    """Получить последние письма в редакцию. status: all, new или reviewed; limit от 1 до 50."""
    if status not in {"all", EditorialLetter.Status.NEW, EditorialLetter.Status.REVIEWED}:
        raise ValueError("status должен быть all, new или reviewed")
    limit = max(1, min(limit, 50))
    queryset = EditorialLetter.objects.select_related("converted_article")
    if status != "all":
        queryset = queryset.filter(status=status)
    return [_letter_payload(letter) for letter in queryset[:limit]]


@mcp.tool()
def get_letter(letter_id: int) -> dict:
    """Получить конкретное письмо в редакцию по ID."""
    try:
        letter = EditorialLetter.objects.select_related("converted_article").get(pk=letter_id)
    except EditorialLetter.DoesNotExist as exc:
        raise ValueError("Письмо не найдено") from exc
    return _letter_payload(letter)


@mcp.tool()
def create_article_draft(
    title: str,
    body: str,
    lead: str = "",
    author_name: str = "Дорогая редакция",
) -> dict:
    """Создать новый черновик. Никогда не публикует материал."""
    article = create_draft(title=title, lead=lead, body=body, author_name=author_name)
    return _article_payload(article)


@mcp.tool()
def update_article_draft(
    article_id: int,
    title: str | None = None,
    lead: str | None = None,
    body: str | None = None,
    author_name: str | None = None,
) -> dict:
    """Изменить существующий черновик. Опубликованный материал менять через MCP нельзя."""
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


@mcp.tool()
def create_draft_from_letter(
    letter_id: int,
    title: str | None = None,
    lead: str | None = None,
    body: str | None = None,
    author_name: str = "Дорогая редакция",
) -> dict:
    """Создать или обновить черновик из письма редакции и сохранить связь с источником."""
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


@mcp.tool()
def mark_letter_reviewed(letter_id: int) -> dict:
    """Отметить письмо как просмотренное, не создавая материал."""
    try:
        letter = EditorialLetter.objects.get(pk=letter_id)
    except EditorialLetter.DoesNotExist as exc:
        raise ValueError("Письмо не найдено") from exc
    if letter.status == EditorialLetter.Status.NEW:
        letter.status = EditorialLetter.Status.REVIEWED
        letter.reviewed_at = timezone.now()
        letter.save(update_fields=["status", "reviewed_at"])
    return _letter_payload(letter)
