from django.urls import path

from ephios.plugins.pages.views import PageView

app_name = "plugins"
urlpatterns = [
    path("page/<slug:slug>/", PageView.as_view(), name="pages:view_page"),
]
