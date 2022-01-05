import collections
import operator
from functools import reduce

from django import template
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from ephios.core.models import AbstractParticipation, EventType, LocalParticipation, UserProfile
from ephios.core.signals import (
    event_info,
    homepage_info,
    register_event_action,
    register_event_bulk_action,
    shift_info,
)
from ephios.core.signup.fallback import (
    catch_signup_method_fails,
    get_signup_method_failed_error_list,
)
from ephios.core.views.signup import request_to_participant
from ephios.extra.colors import get_eventtype_color_style

register = template.Library()


@register.filter(name="reverse_signup_action")
def reverse_signup_action(request, shift):
    return request_to_participant(request).reverse_signup_action(shift)


@register.filter(name="participation_from_request")
def participation_from_request(request, shift):
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


@register.simple_tag
def setvar(value=None):
    """
    as an alternative to using with blocks and template, use
    `{% setvar value|filter:param as var %}` to save a value to a variable in a template.
    The builtin `firstof` doesn't work, because it converts values to strings.
    From here: https://pythoncircle.com/post/701/how-to-set-a-variable-in-django-template/
    """
    return value


@register.filter(name="can_sign_up")
@catch_signup_method_fails(default=False)
def can_sign_up(request, shift):
    return shift.signup_method.can_sign_up(request_to_participant(request))


@register.filter(name="can_customize_signup")
@catch_signup_method_fails(default=False)
def can_customize_signup(request, shift):
    return shift.signup_method.can_customize_signup(request_to_participant(request))


@register.filter(name="signup_errors")
@catch_signup_method_fails(default=get_signup_method_failed_error_list)
def signup_errors(request, shift):
    return set(
        shift.signup_method.get_signup_errors(request_to_participant(request))
        + shift.signup_method.get_decline_errors(request_to_participant(request))
    )


@register.filter(name="can_decline")
@catch_signup_method_fails(default=False)
def can_decline(request, shift):
    return shift.signup_method.can_decline(request_to_participant(request))


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
    return list(map(lambda item: mark_safe(item[1]), results))


@register.simple_tag(name="homepage_plugin_content")
def homepage_plugin_content(request):
    results = homepage_info.send(None, request=request)
    return list(map(lambda item: mark_safe(item[1]), results))


@register.simple_tag(name="event_plugin_actions")
def event_plugin_actions(event):
    html = ""
    for _, actions in register_event_action.send(None):
        html += "".join(
            [
                f"<li><a class='dropdown-item' href='{reverse(action['url'], kwargs=dict(pk=event.id))}'><span class='fas {action['icon']}'></span> {action['label']}</a></li>"
                for action in actions
            ]
        )
    return mark_safe(html)
