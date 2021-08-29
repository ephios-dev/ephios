from django.urls import path

from ephios.plugins.qualification_management.views import (
    QualificationCreateView,
    QualificationImportView,
    QualificationListView,
    QualificationUpdateView,
)

app_name = "qualification_management"
urlpatterns = [
    path(
        "settings/qualifications/",
        QualificationListView.as_view(),
        name="settings_qualification_list",
    ),
    path(
        "settings/qualifications/import/",
        QualificationImportView.as_view(),
        name="settings_qualification_import",
    ),
    path(
        "settings/qualifications/<int:pk>/edit/",
        QualificationUpdateView.as_view(),
        name="settings_qualification_edit",
    ),
    path(
        "settings/qualifications/create/",
        QualificationCreateView.as_view(),
        name="settings_qualification_create",
    ),
]
