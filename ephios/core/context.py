try:
    import importlib_metadata  # importlib is broken on python3.8, using backport
except ImportError:
    import importlib.metadata as importlib_metadata

from django.conf import settings
from django.utils.translation import get_language

from ephios.core.models import AbstractParticipation
from ephios.core.signals import footer_link, nav_link

# suggested in https://github.com/python-poetry/poetry/issues/273
EPHIOS_VERSION = "v" + importlib_metadata.version("ephios")


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
        "ephios_version": EPHIOS_VERSION,
        "SITE_URL": settings.GET_SITE_URL(),
        "PWA_APP_ICONS": settings.PWA_APP_ICONS,
    }
