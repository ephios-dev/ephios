from django import template

from service_management.models import Participation

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
    participation = Participation.objects.filter(user=user, shift=shift).first()
    if participation:
        if participation.accepted:
            return "confirmed"
        else:
            return "registered"
    return None
