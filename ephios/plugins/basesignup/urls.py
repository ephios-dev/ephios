from django.urls import path

from ephios.user_management.signup.disposition import AddUserView, DispositionView

# TODO move this url definition to core

app_name = "basesignup"
urlpatterns = [
    path(
        "shifts/<int:pk>/disposition/",
        DispositionView.as_view(),
        name="shift_disposition",
    ),
    path(
        "shifts/<int:pk>/disposition/add-user/",
        AddUserView.as_view(),
        name="shift_disposition_add_user",
    ),
]
