from django import template
from django.utils.translation import gettext_lazy as _

from ephios.core.models.events import AbstractParticipation, Shift
from ephios.plugins.questionnaires.models import Answer, Question

register = template.Library()


@register.filter("answer_text")
def answer_text(answer):
    return ", ".join(answer) if isinstance(answer, list) else answer


@register.filter("required_text")
def required_text(question: Question):
    return _("required") if question.required else _("optional")


@register.simple_tag(name="all_answers")
def all_answers(question: Question, shift: Shift):
    return Answer.objects.filter(
        participation__shift=shift,
        participation__state=AbstractParticipation.States.CONFIRMED,
        question=question,
    ).values_list("answer", flat=True)


@register.simple_tag(name="aggregate_answers")
def aggregate_answers(question, shift):
    user_answers = all_answers(question, shift)

    aggregated = {}

    for user_answer in user_answers:
        if not isinstance(user_answer, list):
            user_answer = [user_answer]

        for answer in user_answer:
            if answer not in aggregated:
                aggregated[answer] = 0

            aggregated[answer] += 1

    return dict(sorted(aggregated.items(), key=lambda item: item[1], reverse=True))
