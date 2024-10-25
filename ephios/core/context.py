from collections import defaultdict

from django.conf import settings
from django.utils.translation import get_language
from dynamic_preferences.registries import global_preferences_registry

from ephios.core.models import AbstractParticipation
from ephios.core.signals import footer_link, html_head, nav_link


def ephios_base_context(request):
    footer = {}
    for _, result in footer_link.send(None, request=request):
        for label, url in result.items():
            footer[label] = url

    nav = []
    nav_groups = defaultdict(list)
    for _, result in nav_link.send(None, request=request):
        for item in result:
            if group := item.get("group"):
                nav_groups[group].append(item)
            else:
                nav.append(item)
    nav_groups.default_factory = None  # cannot loop defaultdicts in django templates

    _html_head = ""
    for _, result in html_head.send(None, request=request):
        _html_head += result

    return {
        "ParticipationStates": AbstractParticipation.States,
        "nav": nav,
        "nav_groups": nav_groups,
        "signalled_html_head": _html_head,
        "footer": footer,
        "LANGUAGE_CODE": get_language(),
        "ephios_version": settings.EPHIOS_VERSION,
        "PWA_APP_ICONS": settings.PWA_APP_ICONS,
        "organization_name": global_preferences_registry.manager()["general__organization_name"],
    }
