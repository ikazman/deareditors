from django import template
from django.utils.safestring import mark_safe
from markdown_it import MarkdownIt

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


@register.filter(name="editorial_markdown")
def editorial_markdown(value):
    """Render only the small Markdown subset used by Dear Editors."""
    return mark_safe(markdown.render(value or ""))
