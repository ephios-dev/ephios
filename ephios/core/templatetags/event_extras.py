import collections
import operator
from functools import reduce

from django import template
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from ephios.core.models import AbstractParticipation, EventType, Shift, UserProfile
from ephios.core.signals import (
    event_action,
    event_info,
    homepage_info,
    register_event_bulk_action,
    shift_info,
)
from ephios.core.signup.fallback import default_on_exception, get_signup_config_invalid_error
from ephios.core.views.signup import request_to_participant
from ephios.extra.colors import get_eventtype_color_style

register = template.Library()


@register.filter(name="reverse_signup_action")
def reverse_signup_action(request, shift: Shift):
    return request_to_participant(request).reverse_signup_action(shift)


@register.filter(name="participation_from_request")
def participation_from_request(request, shift: Shift):
    return request_to_participant(request).participation_for(shift)


@register.filter(name="participation_css_style")
def participation_css_style(participation):
    if participation:
        return {
            AbstractParticipation.States.USER_DECLINED: "danger",
            AbstractParticipation.States.RESPONSIBLE_REJECTED: "danger",
            AbstractParticipation.States.REQUESTED: "warning",
            AbstractParticipation.States.CONFIRMED: "success",
            AbstractParticipation.States.GETTING_DISPATCHED: "(invalid)",
        }[participation.state]
    return "(invalid)"


@register.filter(name="participation_mannequin_style")
def participation_mannequin_style(participation):
    if participation:
        return {
            AbstractParticipation.States.USER_DECLINED: "denied",
            AbstractParticipation.States.RESPONSIBLE_REJECTED: "denied",
            AbstractParticipation.States.REQUESTED: "requested",
            AbstractParticipation.States.CONFIRMED: "confirmed",
            AbstractParticipation.States.GETTING_DISPATCHED: "neutral",
        }[participation.state]
    return "neutral"


@register.filter(name="can_sign_up")
@default_on_exception(default=False)
def can_sign_up(request, shift: Shift):
    participant = request_to_participant(request)
    return shift.signup_flow.get_validator(participant).can_sign_up()


@register.filter(name="can_customize_signup")
@default_on_exception(default=False)
def can_customize_signup(request, shift: Shift):
    participant = request_to_participant(request)
    return shift.signup_flow.get_validator(participant).can_customize_signup()


@register.filter(name="signup_action_errors")
@default_on_exception(default=lambda: [get_signup_config_invalid_error()])
def signup_action_errors(request, shift: Shift):
    validator = shift.signup_flow.get_validator(request_to_participant(request))
    return validator.get_action_errors()


@register.filter(name="can_decline")
@default_on_exception(default=False)
def can_decline(request, shift: Shift):
    participant = request_to_participant(request)
    return shift.signup_flow.get_validator(participant).can_decline()


@register.filter(name="confirmed_participations")
def confirmed_participations(user: UserProfile):
    # can't use order_by, as postgres gets confused when using the
    # `start_time` coalesce, the shift select related and order_by on start_time at the same time.
    return sorted(
        user.participations.filter(state=AbstractParticipation.States.CONFIRMED)
        .filter(end_time__gte=timezone.now())
        .select_related("shift", "shift__event"),
        key=operator.attrgetter("start_time", "end_time"),
    )


@register.filter(name="event_list_signup_state_counts")
def event_list_signup_state_counts(event):
    """
    Using the annotations on the event queryset in the event list view,
    return a counter counting states for a users participations for shifts of an event.
    """
    # the counter is nice because we can loop over it in the template and only get non-zero count states
    counter = collections.Counter()
    for state in AbstractParticipation.States:
        if count := getattr(event, f"state_{state}_count", 0):
            counter[state] = count
    return counter


@register.simple_tag(name="event_bulk_actions")
def event_bulk_actions():
    html = ""
    for _, actions in register_event_bulk_action.send(None):
        html += "".join(
            [
                f"<button class='btn btn-secondary me-1' type='submit' name='{action['url']}' formaction='{action['url']}'><span class='fa {action['icon']}'></span> {action['label']}</button>"
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


@register.simple_tag(name="event_plugin_content")
def event_plugin_content(event, request):
    results = event_info.send(None, event=event, request=request)
    return list(map(lambda item: mark_safe(item[1]), results))


@register.simple_tag(name="shift_plugin_content")
def shift_plugin_content(shift, request):
    results = shift_info.send(None, shift=shift, request=request)
    return [result[1] for result in results if result[1] is not None]


@register.simple_tag(name="homepage_plugin_content")
def homepage_plugin_content(request):
    results = homepage_info.send(None, request=request)
    return list(map(lambda item: mark_safe(item[1]), results))


@register.simple_tag(name="event_plugin_actions")
def event_plugin_actions(event_detail_view):
    html = ""
    for _, actions in event_action.send(
        None, event=event_detail_view.object, request=event_detail_view.request
    ):
        html += "".join(
            [
                f"<li><a class='dropdown-item' href='{action['url']}'><span class='fas {action['icon']}'></span> {action['label']}</a></li>"
                for action in actions
            ]
        )
    return mark_safe(html)
