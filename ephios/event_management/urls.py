from django.urls import path

import ephios.event_management.views.bulk
import ephios.event_management.views.event
import ephios.event_management.views.shift
import ephios.event_management.views.signup
from ephios.event_management import pdf
from ephios.event_management.ical import EventFeed, user_event_feed_view
from ephios.event_management.views.eventtype import (
    EventTypeCreateView,
    EventTypeDeleteView,
    EventTypeListView,
    EventTypeUpdateView,
)
from ephios.event_management.views.settings import GeneralSettingsView
from ephios.event_management.views.shift import ShiftConfigurationFormView

app_name = "event_management"
urlpatterns = [
    path("", ephios.event_management.views.event.HomeView.as_view(), name="index"),
    path("events/", ephios.event_management.views.event.EventListView.as_view(), name="event_list"),
    path(
        "events/<int:pk>/edit/",
        ephios.event_management.views.event.EventUpdateView.as_view(),
        name="event_edit",
    ),
    path(
        "events/<int:pk>/delete/",
        ephios.event_management.views.event.EventDeleteView.as_view(),
        name="event_delete",
    ),
    path(
        "events/<int:pk>/",
        ephios.event_management.views.event.EventDetailView.as_view(),
        name="event_detail",
    ),
    path(
        "events/<int:pk>/createshift/",
        ephios.event_management.views.shift.ShiftCreateView.as_view(),
        name="event_createshift",
    ),
    path(
        "events/<int:pk>/activate/",
        ephios.event_management.views.event.EventActivateView.as_view(),
        name="event_activate",
    ),
    path("events/<int:pk>/pdf/", pdf.EventDetailPDFView.as_view(), name="event_detail_pdf"),
    path(
        "events/<int:pk>/copy",
        ephios.event_management.views.event.EventCopyView.as_view(),
        name="event_copy",
    ),
    path(
        "events/create/<int:type>/",
        ephios.event_management.views.event.EventCreateView.as_view(),
        name="event_create",
    ),
    path(
        "events/past/",
        ephios.event_management.views.event.EventArchiveView.as_view(),
        name="event_list_past",
    ),
    path(
        "events/delete",
        ephios.event_management.views.bulk.EventBulkDeleteView.as_view(),
        name="event_bulk_delete",
    ),
    path(
        "shifts/<int:pk>/signup-action/",
        ephios.event_management.views.signup.ShiftSignupView.as_view(),
        name="signup_action",
    ),
    path(
        "shifts/<int:pk>/edit/",
        ephios.event_management.views.shift.ShiftUpdateView.as_view(),
        name="shift_edit",
    ),
    path(
        "shifts/<int:pk>/delete/",
        ephios.event_management.views.shift.ShiftDeleteView.as_view(),
        name="shift_delete",
    ),
    path(
        "signup_methods/<slug:slug>/configuration_form/",
        ShiftConfigurationFormView.as_view(),
        name="signupmethod_configurationform",
    ),
    path("calendar/", EventFeed(), name="event_feed"),
    path("calendar/<str:calendar_token>/", user_event_feed_view, name="user_event_feed"),
    path(
        "extra/rruleoccurrence",
        ephios.event_management.views.event.RRuleOccurrenceView.as_view(),
        name="rrule_occurrences",
    ),
    path("settings/general/", GeneralSettingsView.as_view(), name="settings_general"),
    path("settings/eventtype/", EventTypeListView.as_view(), name="settings_eventtype_list"),
    path(
        "settings/eventtype/create/",
        EventTypeCreateView.as_view(),
        name="settings_eventtype_create",
    ),
    path(
        "settings/eventtype/<int:pk>/edit/",
        EventTypeUpdateView.as_view(),
        name="setting_eventtype_edit",
    ),
    path(
        "settings/eventtype/<int:pk>/delete/",
        EventTypeDeleteView.as_view(),
        name="setting_eventtype_delete",
    ),
]
