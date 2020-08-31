from django.urls import path

from event_management import views
from event_management.ical import EventFeed, UserEventFeed, user_event_feed_view
from event_management.views import ShiftConfigurationFormView

app_name = "event_management"
urlpatterns = [
    path("", views.HomeView.as_view(), name="index"),
    path("events/", views.EventListView.as_view(), name="event_list"),
    path("events/<int:pk>/edit/", views.EventUpdateView.as_view(), name="event_edit"),
    path("events/<int:pk>/delete/", views.EventDeleteView.as_view(), name="event_delete"),
    path("events/<int:pk>/", views.EventDetailView.as_view(), name="event_detail"),
    path("events/<int:pk>/createshift/", views.ShiftCreateView.as_view(), name="event_createshift"),
    path("events/<int:pk>/activate/", views.EventActivateView.as_view(), name="event_activate"),
    path("events/create/", views.EventCreateView.as_view(), name="event_create"),
    path("shifts/<int:pk>/register/", views.ShiftSignupView.as_view(), name="shift_register",),
    path("shifts/<int:pk>/edit/", views.ShiftUpdateView.as_view(), name="shift_edit",),
    path("shifts/<int:pk>/delete/", views.ShiftDeleteView.as_view(), name="shift_delete",),
    path(
        "shifts/<int:pk>/user_decline/", views.ShiftDeclineView.as_view(), name="shift_user_decline"
    ),
    path(
        "signup_methods/<slug:slug>/configuration_form/",
        ShiftConfigurationFormView.as_view(),
        name="signupmethod_configurationform",
    ),
    path("calendar/", EventFeed(), name="event_feed"),
    path("calendar/<str:calendar_token>/", user_event_feed_view, name="user_event_feed"),
]
