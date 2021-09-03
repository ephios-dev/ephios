from django.urls import path

from ephios.plugins.qualification_management.views import (
    QualificationCategorySetUpdateView,
    QualificationCreateView,
    QualificationDeleteView,
    QualificationExportFixtureView,
    QualificationImportView,
    QualificationListView,
    QualificationReassignmentView,
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
        "settings/qualifications/<int:pk>/delete/",
        QualificationDeleteView.as_view(),
        name="settings_qualification_delete",
    ),
    path(
        "settings/qualifications/create/",
        QualificationCreateView.as_view(),
        name="settings_qualification_create",
    ),
    path(
        "settings/qualifications/categories/",
        QualificationCategorySetUpdateView.as_view(),
        name="settings_qualification_categories",
    ),
    path(
        "settings/qualifications/reassign/",
        QualificationReassignmentView.as_view(),
        name="settings_qualification_reassignment",
    ),
    path(
        "settings/qualifications/export/",
        QualificationExportFixtureView.as_view(),
        name="settings_qualification_export",
    ),
]
