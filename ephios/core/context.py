import importlib

from django.conf import settings
from django.utils.translation import get_language

from ephios.core.models import AbstractParticipation
from ephios.core.signals import footer_link

# suggested in https://github.com/python-poetry/poetry/issues/273
EPHIOS_VERSION = "v" + importlib.metadata.version("ephios")


def ephios_base_context(request):
    footer = {}
    for _, result in footer_link.send(None, request=request):
        for label, url in result.items():
            footer[label] = url

    return {
        "ParticipationStates": AbstractParticipation.States,
        "footer": footer,
        "LANGUAGE_CODE": get_language(),
        "ephios_version": EPHIOS_VERSION,
        "SITE_URL": settings.SITE_URL,
        "PWA_APP_ICONS": settings.PWA_APP_ICONS,
    }
