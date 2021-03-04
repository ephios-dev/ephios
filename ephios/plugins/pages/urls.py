from django.urls import path

from ephios.plugins.pages.views import PageListView, PageView

app_name = "pages"
urlpatterns = [
    path("page/<slug:slug>/", PageView.as_view(), name="page_detail"),
    path("settings/pages/", PageListView.as_view(), name="settings_page_list"),
]
