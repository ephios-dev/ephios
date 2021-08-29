from django.urls import path

from ephios.plugins.qualification_management.views import (
    QualificationImportView,
    QualificationListView,
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
]
