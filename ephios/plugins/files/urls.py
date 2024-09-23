from django.urls import path

from ephios.plugins.files.views import (
    DocumentCreateView,
    DocumentDeleteView,
    DocumentListView,
    DocumentUpdateView,
    DocumentView,
)

app_name = "files"
urlpatterns = [
    path("document/<int:pk>/", DocumentView.as_view(), name="document"),
    path("settings/documents/", DocumentListView.as_view(), name="settings_document_list"),
    path(
        "settings/documents/create/", DocumentCreateView.as_view(), name="settings_document_create"
    ),
    path(
        "settings/documents/<int:pk>/edit/",
        DocumentUpdateView.as_view(),
        name="settings_document_edit",
    ),
    path(
        "settings/documents/<int:pk>/delete/",
        DocumentDeleteView.as_view(),
        name="settings_document_delete",
    ),
]
