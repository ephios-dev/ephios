from django.urls import path

from ephios.event_management import pdf, views
from ephios.event_management.ical import EventFeed, user_event_feed_view
from ephios.event_management.views import ShiftConfigurationFormView

app_name = "event_management"
urlpatterns = [
    path("", views.HomeView.as_view(), name="index"),
    path("events/", views.EventListView.as_view(), name="event_list"),
    path("events/<int:pk>/edit/", views.EventUpdateView.as_view(), name="event_edit"),
    path("events/<int:pk>/delete/", views.EventDeleteView.as_view(), name="event_delete"),
    path("events/<int:pk>/", views.EventDetailView.as_view(), name="event_detail"),
    path("events/<int:pk>/createshift/", views.ShiftCreateView.as_view(), name="event_createshift"),
    path("events/<int:pk>/activate/", views.EventActivateView.as_view(), name="event_activate"),
    path("events/<int:pk>/pdf/", pdf.EventDetailPDFView.as_view(), name="event_detail_pdf"),
    path("events/create/", views.EventCreateView.as_view(), name="event_create"),
    path("events/past/", views.EventArchiveView.as_view(), name="event_list_past"),
    path(
        "shifts/<int:pk>/signup-action/",
        views.ShiftSignupView.as_view(),
        name="shift_action",
    ),
    path(
        "shifts/<int:pk>/edit/",
        views.ShiftUpdateView.as_view(),
        name="shift_edit",
    ),
    path(
        "shifts/<int:pk>/delete/",
        views.ShiftDeleteView.as_view(),
        name="shift_delete",
    ),
    path(
        "signup_methods/<slug:slug>/configuration_form/",
        ShiftConfigurationFormView.as_view(),
        name="signupmethod_configurationform",
    ),
    path("calendar/", EventFeed(), name="event_feed"),
    path("calendar/<str:calendar_token>/", user_event_feed_view, name="user_event_feed"),
]
