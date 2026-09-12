from django.db import transaction
from django.utils import timezone

from .models import Article, EditorialLetter


SIGNOFF = "Будем наблюдать."


def normalize_article_body(body: str) -> str:
    body = body.rstrip()
    lines = body.splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    if lines and lines[-1].strip().casefold() == SIGNOFF.casefold():
        lines.pop()
        while lines and not lines[-1].strip():
            lines.pop()
    return "\n".join(lines).rstrip()


def create_draft(*, title: str, body: str, lead: str = "", author_name: str = "Дорогая редакция") -> Article:
    title = title.strip()
    if not title:
        raise ValueError("Заголовок не может быть пустым.")
    body = normalize_article_body(body)
    if not body:
        raise ValueError("Текст заметки не может быть пустым.")

    return Article.objects.create(
        title=title,
        lead=lead.strip(),
        body=body,
        author_name=author_name.strip() or "Дорогая редакция",
        status=Article.Status.DRAFT,
    )


def update_draft(
    article: Article,
    *,
    title: str | None = None,
    lead: str | None = None,
    body: str | None = None,
    author_name: str | None = None,
) -> Article:
    if article.status != Article.Status.DRAFT:
        raise ValueError("MCP может изменять только черновики.")

    if title is not None:
        title = title.strip()
        if not title:
            raise ValueError("Заголовок не может быть пустым.")
        article.title = title
    if lead is not None:
        article.lead = lead.strip()
    if body is not None:
        normalized = normalize_article_body(body)
        if not normalized:
            raise ValueError("Текст заметки не может быть пустым.")
        article.body = normalized
    if author_name is not None:
        article.author_name = author_name.strip() or "Дорогая редакция"

    article.save()
    return article


@transaction.atomic
def create_or_update_draft_from_letter(
    letter: EditorialLetter,
    *,
    title: str | None = None,
    lead: str | None = None,
    body: str | None = None,
    author_name: str = "Дорогая редакция",
) -> Article:
    letter = EditorialLetter.objects.select_for_update().select_related("converted_article").get(pk=letter.pk)

    if letter.converted_article_id:
        article = letter.converted_article
        if article.status != Article.Status.DRAFT:
            raise ValueError("Письмо уже связано с опубликованным материалом; MCP не будет его менять.")
        update_draft(
            article,
            title=title,
            lead=lead,
            body=body,
            author_name=author_name,
        )
    else:
        article = create_draft(
            title=title or "До редакции дошел новый слух",
            lead=lead or "",
            body=body if body is not None else letter.body,
            author_name=author_name,
        )
        letter.converted_article = article

    if letter.status == EditorialLetter.Status.NEW:
        letter.status = EditorialLetter.Status.REVIEWED
        letter.reviewed_at = timezone.now()

    letter.save(update_fields=["status", "reviewed_at", "converted_article"])
    return article
