from urllib.parse import urljoin

from django import template
from dynamic_preferences.registries import global_preferences_registry

from ephios.core.dynamic import dynamic_settings
from ephios.core.models.users import IdentityProvider

register = template.Library()


@register.simple_tag
def available_settings_sections(request):
    from ephios.core.views.settings import get_available_settings_sections

    return get_available_settings_sections(request)


@register.simple_tag
def identity_providers():
    return IdentityProvider.objects.all()


@register.simple_tag
def site_url():
    return dynamic_settings.SITE_URL


@register.simple_tag
def organization_name():
    return global_preferences_registry.manager().get("general__organization_name")


@register.filter
def make_absolute(location):
    return urljoin(dynamic_settings.SITE_URL, location)


@register.filter
def as_brand_static_path(path):
    # TODO check that the item at the path exists. if not, try with the default brand static path
    return f"{dynamic_settings.BRAND_STATIC_PATH}{path}"
