from django import template
from django.utils.safestring import mark_safe

from ephios.event_management.models import AbstractParticipation

register = template.Library()


@register.filter(name="shift_status")
def shift_status(shift, user):
    participation = user.as_participant().participation_for(shift)
    if participation is not None:
        color = {
            AbstractParticipation.States.USER_DECLINED: "text-danger",
            AbstractParticipation.States.RESPONSIBLE_REJECTED: "text-danger",
            AbstractParticipation.States.REQUESTED: "text-warning",
            AbstractParticipation.States.CONFIRMED: "text-success",
        }[participation.state]
        return mark_safe(f'<span class="{color}">{participation.get_state_display()}</span><br>')
    return ""


@register.filter(name="can_sign_up")
def can_sign_up(shift, user):
    return shift.signup_method.can_sign_up(user.as_participant())


@register.filter(name="render_shift_state")
def render_shift_state(shift, request):
    return shift.signup_method.render_shift_state(request)


@register.filter(name="signup_errors")
def signup_errors(shift, user):
    return shift.signup_method.get_signup_errors(user.as_participant())


@register.filter(name="can_decline")
def can_decline(shift, user):
    return shift.signup_method.can_decline(user.as_participant())


@register.filter(name="decline_errors")
def decline_errors(shift, user):
    return shift.signup_method.get_decline_errors(user.as_participant())
