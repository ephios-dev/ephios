from django.urls import include, path

from ephios.plugins.guests.views import (
    GuestEventDetailView,
    GuestRegistrationView,
    GuestUserShiftActionView,
)

app_name = "guests"
urlpatterns = [
    path(
        "guests/register/<int:event_id>/<slug:public_signup_token>/",
        GuestRegistrationView.as_view(),
        name="register",
    ),
    path(
        "guests/<guest_access_token>/",
        include(
            [
                path("", GuestEventDetailView.as_view(), name="event_detail"),
                path(
                    "shifts/<int:pk>/signup-action/",
                    GuestUserShiftActionView.as_view(),
                    name="signup_action",
                ),
            ]
        ),
    ),
]
