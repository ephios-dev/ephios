from django.urls import path

from ephios.plugins.basesignup.signup import RequestConfirmDispositionView

app_name = "basesignup"
urlpatterns = [
    path(
        "shifts/<int:pk>/disposition/requestconfirm",
        RequestConfirmDispositionView.as_view(),
        name="shift_disposition_requestconfirm",
    ),
]
