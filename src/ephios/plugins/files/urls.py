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
    path("documents/<int:pk>/", DocumentView.as_view(), name="document_detail"),
    path("documents/", DocumentListView.as_view(), name="document_list"),
    path("documents/create/", DocumentCreateView.as_view(), name="document_create"),
    path(
        "documents/<int:pk>/edit/",
        DocumentUpdateView.as_view(),
        name="document_edit",
    ),
    path(
        "documents/<int:pk>/delete/",
        DocumentDeleteView.as_view(),
        name="document_delete",
    ),
]
