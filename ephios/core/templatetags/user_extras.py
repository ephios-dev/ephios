from django import template
from dynamic_preferences.registries import global_preferences_registry

from ephios.core.consequences import editable_consequences
from ephios.core.signup import get_conflicting_participations

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


@register.filter(name="qualifications_for_category")
def render_qualifications_for_category(userprofile, category_id):
    return ", ".join(
        map(
            lambda grant: grant.qualification.abbreviation,
            getattr(userprofile, f"qualifications_for_category_{category_id}"),
        )
    )


@register.filter(name="get_relevant_qualifications")
def get_relevant_qualifications(qualification_queryset):
    global_preferences = global_preferences_registry.manager()
    qs = qualification_queryset.filter(
        category__in=global_preferences["general__relevant_qualification_categories"]
    )
    return qs.values_list("abbreviation", flat=True)


@register.filter(name="conflicting_shifts")
def participant_conflicting_shifts(participant, shift):
    return get_conflicting_participations(shift, participant).values_list(
        "shift__event__title", flat=True
    )
