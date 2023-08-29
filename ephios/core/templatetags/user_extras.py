from django import template
from django.db.models import Count, Q
from django.utils import timezone
from guardian.shortcuts import get_objects_for_user

from ephios.core.consequences import editable_consequences, pending_consequences
from ephios.core.models import AbstractParticipation, Shift
from ephios.core.signup.methods import get_conflicting_participations

register = template.Library()


@register.filter(name="editable_consequences")
def editable_consequences_tag(user, states=None):
    qs = editable_consequences(user)
    if states:
        qs = qs.filter(state__in=states.split(" "))
    return qs


register.filter(name="pending_consequences", filter_func=pending_consequences)


@register.filter(name="workhour_items")
def workhour_items(user):
    return user.get_workhour_items()


@register.filter(name="abbreviations_to_show_with_user")
def abbreviations_to_show_with_user(qualification_queryset):
    qs = qualification_queryset.filter(category__show_with_user=True).order_by(
        "category", "abbreviation"
    )
    return qs.values_list("abbreviation", flat=True)


@register.filter(name="conflicting_participations")
def participation_conflicts(participation):
    return get_conflicting_participations(
        participant=participation.participant,
        shift=participation.shift,
        start_time=participation.start_time,
        end_time=participation.end_time,
    ).values_list("shift__event__title", flat=True)


@register.filter(name="shifts_needing_disposition")
def shifts_needing_disposition(user):
    return (
        Shift.objects.filter(
            event__in=get_objects_for_user(
                user,
                perms=["core.change_event"],
            ),
            end_time__gt=timezone.now(),
        )
        .annotate(
            request_count=Count(
                "participations",
                filter=Q(participations__state=AbstractParticipation.States.REQUESTED),
            )
        )
        .filter(request_count__gt=0)
    )


@register.filter(name="intersects")
def intersects(a, b):
    return bool(set(a) & set(b))


@register.filter(name="has_permission")
def group_has_permission(group, permission):
    app_label, codename = permission.split(".")
    return group.permissions.filter(content_type__app_label=app_label, codename=codename).exists()
