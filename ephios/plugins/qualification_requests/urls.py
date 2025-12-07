from django.urls import path

from ephios.plugins.qualification_requests.views import QualificationRequestView

app_name = "qualification_requests"

urlpatterns = [
    path(
        "settings/qualifications/requests/create/",
        QualificationRequestView.as_view(),
        name="qualification_requests_create_own",
    ),
]
