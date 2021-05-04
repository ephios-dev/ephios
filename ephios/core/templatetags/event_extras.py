import collections
from functools import reduce

from django import template
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from ephios.core.models import AbstractParticipation, EventType, LocalParticipation
from ephios.core.signals import register_event_bulk_action
from ephios.core.views.signup import request_to_participant
from ephios.extra.colors import get_eventtype_color_style

register = template.Library()


@register.filter(name="reverse_signup_action")
def reverse_signup_action(request, shift):
    return request_to_participant(request).reverse_signup_action(shift)


@register.filter(name="shift_status")
def shift_status(request, shift):
    participation = request_to_participant(request).participation_for(shift)
    if participation is not None:
        color = {
            AbstractParticipation.States.USER_DECLINED: "text-danger",
            AbstractParticipation.States.RESPONSIBLE_REJECTED: "text-danger",
            AbstractParticipation.States.REQUESTED: "text-warning",
            AbstractParticipation.States.CONFIRMED: "text-success",
            AbstractParticipation.States.GETTING_DISPATCHED: "text-secondary",
        }[participation.state]
        return mark_safe(f'<span class="{color}">{participation.get_state_display()}</span><br>')
    return ""


@register.filter(name="can_sign_up")
def can_sign_up(request, shift):
    return shift.signup_method.can_sign_up(request_to_participant(request))


@register.filter(name="render_shift_state")
def render_shift_state(request, shift):
    return shift.signup_method.render_shift_state(request)


@register.filter(name="signup_errors")
def signup_errors(request, shift):
    return shift.signup_method.get_signup_errors(request_to_participant(request))


@register.filter(name="can_decline")
def can_decline(request, shift):
    return shift.signup_method.can_decline(request_to_participant(request))


@register.filter(name="decline_errors")
def decline_errors(request, shift):
    return shift.signup_method.get_decline_errors(request_to_participant(request))


@register.filter(name="confirmed_shifts")
def confirmed_shifts(user):
    return (
        user.get_shifts(with_participation_state_in=[AbstractParticipation.States.CONFIRMED])
        .filter(end_time__gte=timezone.now())
        .order_by("start_time")
    )


@register.filter(name="event_signup_state_counts")
def event_signup_state_counts(event, user):
    """
    Return a counter counting states for a users participations for shifts of an event.
    Uses None as key for no participation info.
    """
    counter = collections.Counter()
    for shift in event.shifts.all():
        for participation in shift.participations.all():
            if isinstance(participation, LocalParticipation) and participation.user_id == user.id:
                counter[participation.state] += 1
                break
    return counter


@register.simple_tag(name="event_bulk_actions")
def event_bulk_actions():
    html = ""
    for _, actions in register_event_bulk_action.send(None):
        html += "".join(
            [
                f"<button class='btn btn-secondary mr-1' type='submit' name='{action['url']}' formaction='{action['url']}'><span class='fa {action['icon']}'></span> {action['label']}</button>"
                for action in actions
            ]
        )
    return format_html(html)


@register.simple_tag(name="eventtype_colors")
def eventtype_colors():
    return mark_safe(
        reduce(
            lambda css, eventtype: css + get_eventtype_color_style(eventtype),
            EventType.objects.all(),
            "",
        )
    )


@register.filter(name="color_css")
def eventtype_color_css(eventtype):
    return get_eventtype_color_style(eventtype)
