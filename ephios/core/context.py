from collections import defaultdict

from django.conf import settings
from django.utils.translation import get_language
from dynamic_preferences.registries import global_preferences_registry

from ephios.core.models import AbstractParticipation
from ephios.core.signals import footer_link, html_head, nav_link, navbar_html


def get_brand_logo_static_path(request):
    from ephios.core.signals import brand_logo_static_path

    for _, result in brand_logo_static_path.send(None, request=request):
        if result:
            return result
    return "ephios/img/ephios-text-black.png"


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
        "brand_logo_static_path": get_brand_logo_static_path(request),
        "signalled_html_head": _html_head,
        "signalled_nav_html": _navbar_additional_html,
        "footer": footer,
        "LANGUAGE_CODE": get_language(),
        "ephios_version": settings.EPHIOS_VERSION,
        "PWA_APP_ICONS": settings.PWA_APP_ICONS,
        "DEBUG": settings.DEBUG,
        "organization_name": global_preferences_registry.manager()["general__organization_name"],
    }
