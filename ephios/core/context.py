from collections import defaultdict

from django.conf import settings
from django.utils.translation import get_language
from dynamic_preferences.registries import global_preferences_registry

from ephios.core.dynamic import dynamic_settings
from ephios.core.models import AbstractParticipation
from ephios.core.signals import footer_link, html_head, nav_link, navbar_html
from ephios.core.views.pwa import get_pwa_app_icons

NAV_USERPROFILE_KEY = "__userprofile__"


def ephios_base_context(request):
    footer = {}
    for _, result in footer_link.send(None, request=request):
        for label, url in result.items():
            footer[label] = url

    nav = []
    nav_groups = defaultdict(list)
    nav_userprofile = []
    for _, result in nav_link.send(None, request=request):
        for item in result:
            if group := item.get("group"):
                if group == NAV_USERPROFILE_KEY:
                    nav_userprofile.append(item)
                else:
                    nav_groups[group].append(item)
            else:
                nav.append(item)
    nav_groups.default_factory = None  # cannot loop defaultdicts in django templates

    _html_head = ""
    for _, result in html_head.send(None, request=request):
        _html_head += result
    _navbar_additional_html = ""
    for _, result in navbar_html.send(None, request=request):
        _navbar_additional_html += result

    return {
        "ParticipationStates": AbstractParticipation.States,
        "nav": nav,
        "nav_groups": nav_groups,
        "nav_userprofile": nav_userprofile,
        "signalled_html_head": _html_head,
        "signalled_nav_html": _navbar_additional_html,
        "footer": footer,
        "LANGUAGE_CODE": get_language(),
        "ephios_version": settings.EPHIOS_VERSION,
        "PWA_APP_ICONS": get_pwa_app_icons(),
        "PWA_APP_SPLASH_SCREEN": [],
        "DEBUG": settings.DEBUG,
        "organization_name": global_preferences_registry.manager()["general__organization_name"],
        "platform_name": dynamic_settings.PLATFORM_NAME,
        "brand_color": dynamic_settings.BRAND_COLOR,
    }
