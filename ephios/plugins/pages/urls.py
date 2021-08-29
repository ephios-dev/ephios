from django.urls import path

from ephios.plugins.pages.views import (
    PageCreateView,
    PageDeleteView,
    PageListView,
    PageUpdateView,
    PageView,
)

app_name = "pages"
urlpatterns = [
    path("page/<slug:slug>/", PageView.as_view(), name="page_detail"),
    path("settings/pages/", PageListView.as_view(), name="settings_page_list"),
    path("settings/pages/create/", PageCreateView.as_view(), name="settings_page_create"),
    path("settings/pages/<int:pk>/edit/", PageUpdateView.as_view(), name="settings_page_edit"),
    path("settings/pages/<int:pk>/delete/", PageDeleteView.as_view(), name="settings_page_delete"),
]
