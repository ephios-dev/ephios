from ephios.helpers.signals import footer_link


def ephios_base_context(request):
    footer = {}
    for receiver, result in footer_link.send(None, request=request):
        for label, url in result.items():
            footer[label] = url

    return {
        "footer": footer,
    }
