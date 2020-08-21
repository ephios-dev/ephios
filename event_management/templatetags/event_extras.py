from django import template

from django.utils.translation import gettext as _

register = template.Library()


@register.filter(name="users_on_shift")
def user_list(resource_position, shift):
    return ", ".join(
        map(
            lambda participation: participation.user.get_full_name(),
            resource_position.participation_set.filter(accepted=True, shift=shift),
        )
    )


@register.filter(name="shift_status")
def shift_status(shift, user):
    participation = user.as_participator().participation_for(shift)
    if participation:
        return participation.get_state_display()
    return "-"


@register.filter(name="can_sign_up")
def can_sign_up(shift, user):
    return shift.signup_method.can_sign_up(user.as_participator())
