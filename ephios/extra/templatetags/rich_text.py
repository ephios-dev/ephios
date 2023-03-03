import bleach
import markdown
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

ALLOWED_TAGS = {
    "a",
    "abbr",
    "acronym",
    "b",
    "blockquote",
    "br",
    "code",
    "div",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "li",
    "ol",
    "p",
    "pre",
    "span",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
}

ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "class"],
    "abbr": ["title"],
    "acronym": ["title"],
    "table": ["width"],
    "td": ["width", "align"],
    "div": ["class"],
    "p": ["class"],
    "span": ["class", "title"],
}

ALLOWED_PROTOCOLS = {"http", "https", "mailto", "tel"}


def markdown_compile(source, excluded_tags=""):
    extensions = ["markdown.extensions.sane_lists", "markdown.extensions.nl2br"]
    tags = ALLOWED_TAGS - set(excluded_tags.split(","))
    return bleach.clean(
        markdown.markdown(source, extensions=extensions),
        tags=tags,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
    )


@register.filter
def rich_text(text: str, excluded_tags=""):
    """
    Processes markdown and cleans HTML in a text input.
    """
    text = str(text)
    linker = bleach.Linker(parse_email=True)
    body_md = linker.linkify(markdown_compile(text, excluded_tags=excluded_tags))
    return mark_safe(body_md)
