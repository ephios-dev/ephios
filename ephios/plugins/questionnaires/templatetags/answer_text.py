from django import template

register = template.Library()


@register.filter("answer_text")
def answer_text(answer):
    return ", ".join(answer) if isinstance(answer, list) else answer
