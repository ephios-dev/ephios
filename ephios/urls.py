from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from ephios.core.plugins import get_all_plugins

urlpatterns = [
    path("", include("ephios.core.urls")),
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("select2/", include("django_select2.urls")),
    path("webpush/", include("webpush.urls")),
    path("api/oauth/", include("ephios.api.access.oauth2_urls", namespace="oauth2_provider")),
    path("api/", include("ephios.api.urls")),
]

# Insert plugin url configs. We can't easily restrict to enabled plugins, as patterns are collected on startup.
for plugin in get_all_plugins():
    try:
        urlpatterns.append(path("", include(plugin.module + ".urls")))
    except ModuleNotFoundError:
        pass

if settings.ENABLE_DEBUG_TOOLBAR:
    import debug_toolbar

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns
