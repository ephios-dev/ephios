from django import template

register = template.Library()

@register.filter(name="user_list")
def user_list(participation_set):
    return ", ".join(map(lambda participation: participation.user.get_full_name(), participation_set.filter(accepted=True)))
