from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.http import JsonResponse
from django.urls import reverse
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView
from dynamic_preferences.registries import global_preferences_registry

from ephios.core.dynamic import dynamic_settings
from ephios.core.templatetags.settings_extras import as_brand_static_path
from ephios.extra.auth import access_exempt


def get_pwa_app_icons():
    return [
        {
            "src": staticfiles_storage.url(as_brand_static_path("appicon-192x.png")),
            "sizes": "192x192",
            "type": "image/png",
            "purpose": "maskable",
        },
        {
            "src": staticfiles_storage.url(as_brand_static_path("appicon-512x.png")),
            "sizes": "512x512",
            "type": "image/png",
            "purpose": "maskable",
        },
        {
            "src": staticfiles_storage.url(as_brand_static_path("appicon-1024x.png")),
            "sizes": "1024x1024",
            "type": "image/png",
            "purpose": "maskable",
        },
        {
            "src": staticfiles_storage.url(
                as_brand_static_path(f"appicon-svg-{'debug' if settings.DEBUG else 'prod'}.svg")
            ),
            "sizes": "any",
            "type": "image/svg+xml",
            "purpose": "any",
        },
    ]


@access_exempt
class PWAManifestView(View):
    def get(self, request, *args, **kwargs):
        org_name = global_preferences_registry.manager().get("general__organization_name")
        manifest_json = {
            "name": f"{dynamic_settings.PLATFORM_NAME} {org_name}",
            "short_name": dynamic_settings.PLATFORM_NAME,
            "description": f"{dynamic_settings.PLATFORM_NAME} manages events for {org_name}",
            "id": "/",
            "start_url": "/",
            "display": "standalone",
            "scope": "/",
            "background_color": "#fff",
            "theme_color": dynamic_settings.BRAND_COLOR,
            "status_bar": "default",
            "dir": "auto",
            "icons": get_pwa_app_icons(),
            "lang": get_language(),
            "shortcuts": [
                {
                    "name": _("Events"),
                    "description": _("Show the event list"),
                    "url": reverse("core:event_list"),
                    "icons": [
                        {
                            "src": staticfiles_storage.url(
                                as_brand_static_path("appicon-192x.png")
                            ),
                            "sizes": "192x192",
                        }
                    ],
                },
            ],
        }
        response = JsonResponse(manifest_json)
        response["Service-Worker-Allowed"] = "/"
        return response


@access_exempt
class ServiceWorkerView(TemplateView):
    template_name = "core/serviceworker.js"
    content_type = "application/javascript"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["offline_url"] = reverse("core:pwa_offline")
        # Cache name: we serve /static/ files with a cache first strategy, so
        # we need to use a new cache name when the static files change with a new ephios version.
        # Also, we need to start a new cache for every user and permission change.
        identity = self.request.user.id if self.request.user.is_authenticated else "anonymous"
        permissions = set(self.request.user.get_all_permissions())
        if self.request.user.is_superuser:
            permissions.add("_pwa:superuser")
        if self.request.user.is_staff:
            permissions.add("_pwa:staff")
        permission_hash = hash(tuple(sorted(permissions)))
        context["cache_name"] = (
            f"ephios-pwa-v{settings.EPHIOS_VERSION}/{identity}-{permission_hash}"
        )
        context["static_url"] = settings.STATIC_URL
        context["enable_cache"] = settings.COMPRESS_ENABLED
        return context


@access_exempt
class OfflineView(TemplateView):
    template_name = "offline.html"
