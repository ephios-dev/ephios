from django.conf import settings
from django.utils.translation import get_language
from dynamic_preferences.registries import global_preferences_registry

from ephios.core.models import AbstractParticipation
from ephios.core.signals import footer_link, nav_link


def ephios_base_context(request):
    footer = {}
    for _, result in footer_link.send(None, request=request):
        for label, url in result.items():
            footer[label] = url

    nav = []
    for _, result in nav_link.send(None, request=request):
        nav += result

    return {
        "ParticipationStates": AbstractParticipation.States,
        "nav": nav,
        "footer": footer,
        "LANGUAGE_CODE": get_language(),
        "ephios_version": settings.EPHIOS_VERSION,
        "PWA_APP_ICONS": settings.PWA_APP_ICONS,
        "organization_name": global_preferences_registry.manager()["general__organization_name"],
    }
