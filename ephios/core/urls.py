from django.urls import path

from ephios.core import pdf
from ephios.core.ical import user_event_feed_view
from ephios.core.signup.disposition import (
    AddPlaceholderParticipantView,
    AddUserView,
    DispositionView,
)
from ephios.core.views.accounts import (
    GroupCreateView,
    GroupDeleteView,
    GroupListView,
    GroupUpdateView,
    UserProfileCreateView,
    UserProfileDeleteView,
    UserProfileListView,
    UserProfilePasswordResetView,
    UserProfileUpdateView,
)
from ephios.core.views.bulk import EventBulkDeleteView
from ephios.core.views.consequences import ConsequenceUpdateView
from ephios.core.views.event import (
    EventActivateView,
    EventArchiveView,
    EventCopyView,
    EventCreateView,
    EventDeleteView,
    EventDetailView,
    EventListTypeSettingView,
    EventNotificationView,
    EventUpdateView,
    HomeView,
    RRuleOccurrenceView,
    current_event_list_view,
)
from ephios.core.views.eventtype import (
    EventTypeCreateView,
    EventTypeDeleteView,
    EventTypeListView,
    EventTypeUpdateView,
)
from ephios.core.views.log import LogView
from ephios.core.views.pwa import manifest, offline, serviceworker
from ephios.core.views.settings import (
    CalendarSettingsView,
    InstanceSettingsView,
    NotificationSettingsView,
    PasswordChangeSettingsView,
    PersonalDataSettingsView,
)
from ephios.core.views.shift import (
    ShiftConfigurationFormView,
    ShiftCreateView,
    ShiftDeleteView,
    ShiftUpdateView,
)
from ephios.core.views.signup import LocalUserShiftActionView
from ephios.core.views.workinghour import (
    OwnWorkingHourView,
    UserProfileWorkingHourView,
    WorkingHourCreateView,
    WorkingHourDeleteView,
    WorkingHourOverview,
    WorkingHourRequestView,
    WorkingHourUpdateView,
)

app_name = "core"
urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("events/", current_event_list_view, name="event_list"),
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
        "events/<int:pk>-<slug:slug>/",
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
    path(
        "events/<int:pk>/notifications/",
        EventNotificationView.as_view(),
        name="event_notifications",
    ),
    path("events/<int:pk>/pdf/", pdf.EventDetailPDFView.as_view(), name="event_detail_pdf"),
    path(
        "events/<int:pk>/copy/",
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
        "events/delete/",
        EventBulkDeleteView.as_view(),
        name="event_bulk_delete",
    ),
    path(
        "shifts/<int:pk>/signup/",
        LocalUserShiftActionView.as_view(),
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
        "signup_method_configuration_form/<int:event_id>/<slug:slug>/",
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
    path(
        "shifts/<int:pk>/disposition/add-placeholder/",
        AddPlaceholderParticipantView.as_view(),
        name="shift_disposition_add_placeholder",
    ),
    path("calendar/<str:calendar_token>/", user_event_feed_view, name="user_event_feed"),
    path(
        "extra/rruleoccurrence/",
        RRuleOccurrenceView.as_view(),
        name="rrule_occurrences",
    ),
    path("settings/data/", PersonalDataSettingsView.as_view(), name="settings_personal_data"),
    path("settings/calendar/", CalendarSettingsView.as_view(), name="settings_calendar"),
    path(
        "settings/notifications/",
        NotificationSettingsView.as_view(),
        name="settings_notifications",
    ),
    path(
        "settings/password_change/",
        PasswordChangeSettingsView.as_view(),
        name="settings_password_change",
    ),
    path("settings/instance/", InstanceSettingsView.as_view(), name="settings_instance"),
    path("settings/eventtypes/", EventTypeListView.as_view(), name="settings_eventtype_list"),
    path(
        "settings/eventtypes/create/",
        EventTypeCreateView.as_view(),
        name="settings_eventtype_create",
    ),
    path(
        "settings/eventtypes/<int:pk>/edit/",
        EventTypeUpdateView.as_view(),
        name="settings_eventtype_edit",
    ),
    path(
        "settings/eventtypes/<int:pk>/delete/",
        EventTypeDeleteView.as_view(),
        name="settings_eventtype_delete",
    ),
    path("groups/", GroupListView.as_view(), name="group_list"),
    path("groups/<int:pk>/edit/", GroupUpdateView.as_view(), name="group_edit"),
    path("groups/<int:pk>/delete/", GroupDeleteView.as_view(), name="group_delete"),
    path("groups/create/", GroupCreateView.as_view(), name="group_add"),
    path(
        "users/",
        UserProfileListView.as_view(),
        name="userprofile_list",
    ),
    path(
        "users/<int:pk>/edit/",
        UserProfileUpdateView.as_view(),
        name="userprofile_edit",
    ),
    path(
        "users/<int:pk>/delete/",
        UserProfileDeleteView.as_view(),
        name="userprofile_delete",
    ),
    path(
        "users/<int:pk>/password_reset/",
        UserProfilePasswordResetView.as_view(),
        name="userprofile_password_reset",
    ),
    path(
        "users/create/",
        UserProfileCreateView.as_view(),
        name="userprofile_create",
    ),
    path(
        "consequences/<int:pk>/edit/",
        ConsequenceUpdateView.as_view(),
        name="consequence_edit",
    ),
    path("log/", LogView.as_view(), name="log"),
    path("manifest.json", manifest, name="pwa_manifest"),
    path("serviceworker.js", serviceworker, name="pwa_serviceworker"),
    path("offline/", offline, name="pwa_offline"),
    path(
        "events/list_type_setting/",
        EventListTypeSettingView.as_view(),
        name="event_list_type_setting",
    ),
    path("workinghours/own/", OwnWorkingHourView.as_view(), name="workinghour_own"),
    path(
        "workinghours/own/request/",
        WorkingHourRequestView.as_view(),
        name="workinghour_request",
    ),
    path("workinghours/", WorkingHourOverview.as_view(), name="workinghour_list"),
    path("workinghours/<int:pk>/edit/", WorkingHourUpdateView.as_view(), name="workinghour_edit"),
    path(
        "workinghours/<int:pk>/delete/", WorkingHourDeleteView.as_view(), name="workinghour_delete"
    ),
    path(
        "workinghours/user/<int:pk>/",
        UserProfileWorkingHourView.as_view(),
        name="workinghour_detail",
    ),
    path(
        "workinghours/user/<int:pk>/add/",
        WorkingHourCreateView.as_view(),
        name="workinghour_add",
    ),
]
