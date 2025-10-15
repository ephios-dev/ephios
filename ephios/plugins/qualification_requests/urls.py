from django.urls import path
from ephios.plugins.qualification_requests.views import (
    QualificationRequestListView,
    QualificationRequestOwnListView,
    QualificationRequestAddView,
    QualificationRequestUpdateView,
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
        "settings/qualifications/requests/add/",
        QualificationRequestAddView.as_view(),
        name="qualification_request_add",
    ),
    path(
        "settings/qualifications/requests/<int:pk>/",
        QualificationRequestUpdateView.as_view(),
        name="qualification_request_update",
    ),
]