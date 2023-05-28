from django import template
from django.conf import settings

from ephios.core.views.settings import get_available_management_settings_sections

register = template.Library()


@register.simple_tag
def available_management_settings_sections(request):
    return get_available_management_settings_sections(request)


@register.simple_tag
def oidc_client_enabled():
    return settings.ENABLE_OIDC_CLIENT
