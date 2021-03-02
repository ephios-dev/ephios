from django import template

from ephios.core.consequences import editable_consequences

register = template.Library()


@register.filter(name="editable_consequences")
def editable_consequences_tag(user, states=None):
    qs = editable_consequences(user)
    if states:
        qs = qs.filter(state__in=states.split(" "))
    return qs


@register.filter(name="workhour_items")
def workhour_items(user):
    return user.get_workhour_items()


@register.filter(name="render_qualifications")
def render_qualifications_from_grants(grant_list):
    return ", ".join(map(lambda grant: grant.qualification.abbreviation, grant_list))
