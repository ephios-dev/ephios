from django import template

from ephios.user_management.consequences import editable_consequences
from ephios.user_management.models import Consequence

register = template.Library()


@register.filter(name="editable_consequences")
def editable_consequences_tag(user, states=None):
    if not states:
        states = " ".join(Consequence.States.values)
    return editable_consequences(user).filter(state__in=states.split(" "))
