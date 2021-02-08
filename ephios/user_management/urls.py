from django.urls import path

from ephios.user_management import pdf
from ephios.user_management.ical import EventFeed, user_event_feed_view
from ephios.user_management.signup.disposition import AddUserView, DispositionView
from ephios.user_management.views.accounts import (
    GroupCreateView,
    GroupDeleteView,
    GroupListView,
    GroupUpdateView,
    ProfileView,
    UserProfileCreateView,
    UserProfileDeleteView,
    UserProfileListView,
    UserProfileSettingsView,
    UserProfileUpdateView,
)
from ephios.user_management.views.bulk import EventBulkDeleteView
from ephios.user_management.views.consequences import ConsequenceUpdateView, WorkingHourRequestView
from ephios.user_management.views.event import (
    EventActivateView,
    EventArchiveView,
    EventCopyView,
    EventCreateView,
    EventDeleteView,
    EventDetailView,
    EventListView,
    EventUpdateView,
    HomeView,
    RRuleOccurrenceView,
)
from ephios.user_management.views.eventtype import (
    EventTypeCreateView,
    EventTypeDeleteView,
    EventTypeListView,
    EventTypeUpdateView,
)
from ephios.user_management.views.settings import GeneralSettingsView
from ephios.user_management.views.shift import (
    ShiftConfigurationFormView,
    ShiftCreateView,
    ShiftDeleteView,
    ShiftUpdateView,
)
from ephios.user_management.views.signup import ShiftSignupView

app_name = "user_management"
urlpatterns = [
    path("", HomeView.as_view(), name="index"),
    path("events/", EventListView.as_view(), name="event_list"),
    path(
        "events/<int:pk>/edit/",
        EventUpdateView.as_view(),
        name="event_edit",
    ),
    path(
        "events/<int:pk>/delete/",
        EventDeleteView.as_view(),
        name="event_delete",
    ),
    path(
        "events/<int:pk>/",
        EventDetailView.as_view(),
        name="event_detail",
    ),
    path(
        "events/<int:pk>/createshift/",
        ShiftCreateView.as_view(),
        name="event_createshift",
    ),
    path(
        "events/<int:pk>/activate/",
        EventActivateView.as_view(),
        name="event_activate",
    ),
    path("events/<int:pk>/pdf/", pdf.EventDetailPDFView.as_view(), name="event_detail_pdf"),
    path(
        "events/<int:pk>/copy",
        EventCopyView.as_view(),
        name="event_copy",
    ),
    path(
        "events/create/<int:type>/",
        EventCreateView.as_view(),
        name="event_create",
    ),
    path(
        "events/past/",
        EventArchiveView.as_view(),
        name="event_list_past",
    ),
    path(
        "events/delete",
        EventBulkDeleteView.as_view(),
        name="event_bulk_delete",
    ),
    path(
        "shifts/<int:pk>/signup-action/",
        ShiftSignupView.as_view(),
        name="signup_action",
    ),
    path(
        "shifts/<int:pk>/edit/",
        ShiftUpdateView.as_view(),
        name="shift_edit",
    ),
    path(
        "shifts/<int:pk>/delete/",
        ShiftDeleteView.as_view(),
        name="shift_delete",
    ),
    path(
        "signup_methods/<slug:slug>/configuration_form/",
        ShiftConfigurationFormView.as_view(),
        name="signupmethod_configurationform",
    ),
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
    path("calendar/", EventFeed(), name="event_feed"),
    path("calendar/<str:calendar_token>/", user_event_feed_view, name="user_event_feed"),
    path(
        "extra/rruleoccurrence",
        RRuleOccurrenceView.as_view(),
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
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/settings", UserProfileSettingsView.as_view(), name="profile_settings"),
    path("groups/", GroupListView.as_view(), name="group_list"),
    path("groups/<int:pk>/edit", GroupUpdateView.as_view(), name="group_edit"),
    path("groups/<int:pk>/delete", GroupDeleteView.as_view(), name="group_delete"),
    path("groups/create", GroupCreateView.as_view(), name="group_add"),
    path(
        "users/",
        UserProfileListView.as_view(),
        name="userprofile_list",
    ),
    path(
        "users/<int:pk>/edit",
        UserProfileUpdateView.as_view(),
        name="userprofile_edit",
    ),
    path(
        "users/<int:pk>/delete",
        UserProfileDeleteView.as_view(),
        name="userprofile_delete",
    ),
    path(
        "users/create/",
        UserProfileCreateView.as_view(),
        name="userprofile_create",
    ),
    path(
        "consequences/<int:pk>/edit",
        ConsequenceUpdateView.as_view(),
        name="consequence_edit",
    ),
    path(
        "profile/requestworkinghour",
        WorkingHourRequestView.as_view(),
        name="request_workinghour",
    ),
]
