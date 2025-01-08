import logging
import os
from functools import lru_cache
from urllib.parse import urljoin

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from dynamic_preferences.registries import global_preferences_registry

from ephios.core.dynamic import dynamic_settings
from ephios.core.models.users import IdentityProvider

register = template.Library()
logger = logging.getLogger(__name__)


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


@lru_cache()
def _static_file_exists(path):
    return bool(finders.find(path))


@register.filter
def as_brand_static_path(path):
    result = os.path.join(dynamic_settings.BRAND_STATIC_PATH, path)
    if not _static_file_exists(result):
        fallback = os.path.join(
            getattr(settings, dynamic_settings.get_default_key("BRAND_STATIC_PATH")), path
        )
        logger.warning(f"could not find brand static file '{result}', using '{fallback}' instead")
        return fallback
    return result
