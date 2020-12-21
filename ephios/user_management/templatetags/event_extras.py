from django import template
from django.utils.safestring import mark_safe


register = template.Library()

@register.filter(name="editable_consequences")
def editable_consequences(user):
    return user.get_shifts(
        with_participation_state_in=[AbstractParticipation.States.CONFIRMED]
    ).order_by("start_time")
