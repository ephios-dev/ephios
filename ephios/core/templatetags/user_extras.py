from django import template

from ephios.core.consequences import editable_consequences, my_pending_consequences

register = template.Library()


@register.filter(name="editable_consequences")
def editable_consequences_tag(user, states=None):
    qs = editable_consequences(user)
    if states:
        qs = qs.filter(state__in=states.split(" "))
    return qs


@register.filter(name="my_pending_consequences")
def my_pending_consequences_tag(user):
    qs = my_pending_consequences(user)
    return qs


@register.filter(name="workhour_items")
def workhour_items(user):
    return user.get_workhour_items()
