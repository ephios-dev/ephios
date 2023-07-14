import functools

from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView
from dynamic_preferences.registries import global_preferences_registry


class PWAManifestView(View):
    def get(self, request, *args, **kwargs):
        org_name = global_preferences_registry.manager().get("general__organization_name")
        manifest_json = {
            "name": f"ephios {org_name}",
            "short_name": "ephios",
            "description": "ephios manages events for medical services",
            "id": "/",
            "start_url": "/",
            "display": "standalone",
            "scope": "/",
            "background_color": "#fff",
            "theme_color": "#ff033f",
            "status_bar": "default",
            "dir": "auto",
            "icons": settings.PWA_APP_ICONS,
            "lang": get_language(),
            "shortcuts": [
                {
                    "name": _("Events"),
                    "description": _("Show the event list"),
                    "url": reverse("core:event_list"),
                    "icons": [{"src": "/static/ephios/img/ephios-192x.png", "sizes": "192x192"}],
                },
            ],
        }
        response = JsonResponse(manifest_json)
        response["Service-Worker-Allowed"] = "/"
        return response


@functools.lru_cache
def serviceworker_js():
    with open(finders.find("ephios/js/serviceworker.js"), "rb") as sw_js:
        return sw_js.read()


class ServiceWorkerView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponse(
            serviceworker_js(),
            content_type="application/javascript",
        )


class OfflineView(TemplateView):
    template_name = "offline.html"
