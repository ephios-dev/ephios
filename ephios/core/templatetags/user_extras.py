from typing import Iterable

from django import template
from django.db.models import Count, Q
from django.utils import timezone
from guardian.shortcuts import get_objects_for_user

from ephios.core.consequences import editable_consequences, pending_consequences
from ephios.core.models import AbstractParticipation, QualificationGrant, Shift
from ephios.core.services.qualification import essential_set_of_qualifications
from ephios.core.signup.flow.participant_validation import get_conflicting_participations

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


@register.filter(name="grants_to_essential_abbreviations")
def grants_to_essential_abbreviations(grants: Iterable[QualificationGrant]):
    return qualifications_to_essential_abbreviations(
        grant.qualification for grant in grants if grant.is_valid()
    )


@register.filter(name="qualifications_to_essential_abbreviations")
def qualifications_to_essential_abbreviations(qualifications):
    essentials = list(essential_set_of_qualifications(qualifications))
    essentials.sort(key=lambda q: (q.category_id, q.abbreviation))
    return list(qualification.abbreviation for qualification in essentials)


@register.filter(name="intersects")
def intersects(a, b):
    return bool(set(a) & set(b))


@register.filter(name="has_permission")
def group_has_permission(group, permission):
    app_label, codename = permission.split(".")
    return group.permissions.filter(content_type__app_label=app_label, codename=codename).exists()


@register.filter(name="not_seen_recently")
def not_seen_recently(userprofile):
    if not userprofile.last_login:
        return True
    return timezone.now() - userprofile.last_login > timezone.timedelta(weeks=25)
