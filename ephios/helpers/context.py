from django.templatetags.static import static
from django.utils.translation import get_language

from ephios.helpers.signals import footer_link


def ephios_base_context(request):
    footer = {}
    for receiver, result in footer_link.send(None, request=request):
        for label, url in result.items():
            footer[label] = url

    datatables_translation_url = None
    if get_language() == "de-de":
        datatables_translation_url = static("datatables/german.json")

    return {"footer": footer, "datatables_translation_url": datatables_translation_url}
