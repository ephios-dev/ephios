from django.urls import path

from ephios.contrib.signup.confirm import RequestConfirmDispositionView

app_name = "contrib"
urlpatterns = [
    path(
        "shifts/<int:pk>/disposition/requestconfirm",
        RequestConfirmDispositionView.as_view(),
        name="shift_disposition_requestconfirm",
    ),
]
