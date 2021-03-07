from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.translation import get_language

from ephios.settings import PWA_APP_ICONS, STATIC_ROOT


def manifest(request):
    manifest_json = {
        "name": "ephios",
        "short_name": "ephios",
        "description": "ephios manages events for medical services",
        "start_url": "/",
        "display": "standalone",
        "scope": "/",
        "orientation": "any",
        "background_color": "#fff",
        "theme_color": "#000",
        "status_bar": "default",
        "dir": "auto",
        "icons": PWA_APP_ICONS,
        "lang": get_language(),
    }
    response = JsonResponse(manifest_json)
    response["Service-Worker-Allowed"] = "/"
    return response


def serviceworker(request):
    return HttpResponse(
        open(STATIC_ROOT + "/ephios/js/serviceworker.js").read(),
        content_type="application/javascript",
    )


def offline(request):
    return render(request, "offline.html")
