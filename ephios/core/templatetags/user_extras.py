from django import template
from django.utils import timezone
from dynamic_preferences.registries import global_preferences_registry
from guardian.shortcuts import get_objects_for_user

from ephios.core.consequences import editable_consequences
from ephios.core.models import AbstractParticipation, Shift
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
    ).order_by("category", "abbreviation")
    return qs.values_list("abbreviation", flat=True)


@register.filter(name="conflicting_shifts")
def participant_conflicting_shifts(participant, shift):
    return get_conflicting_participations(shift, participant).values_list(
        "shift__event__title", flat=True
    )


@register.filter(name="shifts_needing_disposition")
def shifts_needing_disposition(user):
    return Shift.objects.filter(
        participations__state=AbstractParticipation.States.REQUESTED,
        event__in=get_objects_for_user(
            user,
            perms=["core.change_event"],
        ),
        end_time__gt=timezone.now(),
    ).distinct()
