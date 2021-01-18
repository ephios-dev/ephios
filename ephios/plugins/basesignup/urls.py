from django.urls import path

from ephios.plugins.basesignup.signup.section_based import (
    SectionBasedAddUserView,
    SectionBasedDispositionView,
)
from ephios.plugins.basesignup.signup.simple import RequestConfirmDispositionView

app_name = "basesignup"
urlpatterns = [
    path(
        "shifts/<int:pk>/disposition/requestconfirm/",
        RequestConfirmDispositionView.as_view(),
        name="shift_disposition_requestconfirm",
    ),
    path(
        "shifts/<int:pk>/disposition/section-based/",
        SectionBasedDispositionView.as_view(),
        name="shift_disposition_section_based",
    ),
    path(
        "shifts/<int:pk>/disposition/section-based/add-user/",
        SectionBasedAddUserView.as_view(),
        name="shift_disposition_add_user_section_based",
    ),
]
