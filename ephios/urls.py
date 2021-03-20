"""ephios URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.i18n import JavaScriptCatalog

from ephios.core.plugins import get_all_plugins

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("select2/", include("django_select2.urls")),
    path("webpush/", include("webpush.urls")),
    path("", include("ephios.core.urls")),
    path("jsi18n.js", JavaScriptCatalog.as_view(packages=["recurrence"]), name="jsi18n"),
]

# Insert plugin url configs. We can't easily restrict to enabled plugins, as patterns are collected on startup.
for plugin in get_all_plugins():
    try:
        urlpatterns.append(path("", include(plugin.module + ".urls")))
    except ModuleNotFoundError:
        pass

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns
