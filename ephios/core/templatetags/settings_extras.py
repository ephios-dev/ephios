from django import template

from ephios.core.views.settings import get_available_management_settings_sections

register = template.Library()


@register.simple_tag
def available_management_settings_sections(request):
    return get_available_management_settings_sections(request)
