from django.urls import path
from ephios.plugins.qualification_requests.views import (
    QualificationRequestListView,
    QualificationRequestOwnListView,
    QualificationRequestOwnCreateView,
    QualificationRequestOwnUpdateView,
    QualificationRequestCheckView,
    QualificationRequestOwnDeleteView,
    QualificationRequestDeleteView,
)

app_name = "qualification_requests"

urlpatterns = [
    path(
        "settings/qualifications/requests/",
        QualificationRequestListView.as_view(),
        name="qualification_requests_list",
    ),
    path(
        "settings/qualifications/requests/own/",
        QualificationRequestOwnListView.as_view(),
        name="qualification_requests_list_own",
    ),
    path(
        "settings/qualifications/requests/create/",
        QualificationRequestOwnCreateView.as_view(),
        name="qualification_requests_create_own",
    ),
    path(
        "settings/qualifications/requests/<int:pk>/edit/",
        QualificationRequestOwnUpdateView.as_view(),
        name="qualification_requests_update_own",
    ),
    path(
        "settings/qualifications/requests/<int:pk>/check/",
        QualificationRequestCheckView.as_view(),
        name="qualification_requests_check",
    ),
    path(
        "settings/qualifications/requests/<int:pk>/deleteown/",
        QualificationRequestOwnDeleteView.as_view(),
        name="qualification_requests_delete_own",
    ),
    path(
        "settings/qualifications/requests/<int:pk>/delete/",
        QualificationRequestDeleteView.as_view(),
        name="qualification_requests_delete",
    ),
]