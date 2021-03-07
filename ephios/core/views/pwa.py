from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.translation import get_language


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
        "icons": settings.PWA_APP_ICONS,
        "lang": get_language(),
    }
    response = JsonResponse(manifest_json)
    response["Service-Worker-Allowed"] = "/"
    return response


with open(settings.STATIC_ROOT + "/ephios/js/serviceworker.js", "rb") as sw_js:
    serviceworker_js = sw_js.read()


def serviceworker(request):
    return HttpResponse(
        serviceworker_js,
        content_type="application/javascript",
    )


def offline(request):
    return render(request, "offline.html")
