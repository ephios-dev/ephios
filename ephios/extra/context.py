import importlib

from django.templatetags.static import static
from django.utils.translation import get_language

from ephios.extra.signals import footer_link
from ephios.settings import SITE_URL

# suggested in https://github.com/python-poetry/poetry/issues/273
EPHIOS_VERSION = "v" + importlib.metadata.version("ephios")


def ephios_base_context(request):
    footer = {}
    for _, result in footer_link.send(None, request=request):
        for label, url in result.items():
            footer[label] = url

    datatables_translation_url = None
    if get_language() == "de-de":
        datatables_translation_url = static("datatables/german.json")

    return {
        "footer": footer,
        "datatables_translation_url": datatables_translation_url,
        "ephios_version": EPHIOS_VERSION,
        "SITE_URL": SITE_URL,
    }
