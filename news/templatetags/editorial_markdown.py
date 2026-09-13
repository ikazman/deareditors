import re

from django import template
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from markdown_it import MarkdownIt

from news.models import ArticleImage

register = template.Library()

markdown = MarkdownIt(
    "commonmark",
    {
        "html": False,
        "linkify": False,
        "typographer": False,
    },
)
markdown.disable(
    [
        "heading",
        "lheading",
        "blockquote",
        "fence",
        "code",
        "hr",
        "image",
        "backticks",
        "autolink",
    ]
)

IMAGE_MARKER_RE = re.compile(r"(?m)^[ \t]*\[\[image:([0-9a-fA-F-]{36})\]\][ \t]*$")


def _render_figure(image):
    layout_class = "article-figure--wide" if image.layout == ArticleImage.Layout.WIDE else "article-figure--measure"
    caption = format_html('<figcaption class="article-figure__caption">{}</figcaption>', image.caption) if image.caption else ""
    return format_html(
        '<figure class="article-figure {}">'
        '<img src="{}" alt="{}" loading="lazy" decoding="async">'
        '{}'
        '</figure>',
        layout_class,
        reverse("article-image", kwargs={"pk": image.pk}),
        image.alt_text,
        mark_safe(caption),
    )


@register.filter(name="editorial_markdown")
def editorial_markdown(value):
    """Render only the small Markdown subset used by Dear Editors."""
    return mark_safe(markdown.render(value or ""))


@register.filter(name="editorial_article")
def editorial_article(article):
    """Render editorial Markdown plus image markers that belong to this article."""
    body = article.body or ""
    images = {str(image.pk): image for image in article.images.all()} if article.pk else {}
    parts = []
    cursor = 0

    for match in IMAGE_MARKER_RE.finditer(body):
        parts.append(markdown.render(body[cursor:match.start()]))
        image = images.get(match.group(1))
        if image is not None:
            parts.append(str(_render_figure(image)))
        cursor = match.end()

    parts.append(markdown.render(body[cursor:]))
    return mark_safe("".join(parts))
