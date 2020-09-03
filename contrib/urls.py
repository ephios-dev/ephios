from django.urls import path

from contrib.signup.confirm import RequestConfirmView
from event_management import views
from event_management.ical import EventFeed, UserEventFeed, user_event_feed_view
from event_management.views import ShiftConfigurationFormView

app_name = "contrib"
urlpatterns = [
    path(
        "shifts/<int:pk>/disposition/requestconfirm",
        RequestConfirmView.as_view(),
        name="shift_disposition_requestconfirm",
    ),
]
