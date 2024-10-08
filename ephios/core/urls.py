from django.urls import path

from ephios.core import pdf
from ephios.core.ical import user_event_feed_view
from ephios.core.services.files import FileTicketView
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
    UserProfilePasswordTokenRevokationView,
    UserProfileUpdateView,
)
from ephios.core.views.auth import (
    IdentityProviderCreateView,
    IdentityProviderDeleteView,
    IdentityProviderDiscoveryView,
    IdentityProviderListView,
    IdentityProviderUpdateView,
    OIDCCallbackView,
    OIDCInitiateView,
    OIDCLoginView,
    OIDCLogoutView,
)
from ephios.core.views.bulk import EventBulkDeleteView
from ephios.core.views.consequences import ConsequenceUpdateView
from ephios.core.views.event import (
    EventActivateView,
    EventCopyView,
    EventCreateView,
    EventDeleteView,
    EventDetailView,
    EventListView,
    EventNotificationView,
    EventUpdateView,
    HomeView,
    RRuleOccurrenceView,
)
from ephios.core.views.eventtype import (
    EventTypeCreateView,
    EventTypeDeleteView,
    EventTypeListView,
    EventTypeUpdateView,
)
from ephios.core.views.healthcheck import HealthCheckView
from ephios.core.views.log import LogView
from ephios.core.views.notifications import (
    NotificationDetailView,
    NotificationListView,
    NotificationMarkAllAsReadView,
    NotificationMarkAsReadView,
)
from ephios.core.views.pwa import OfflineView, PWAManifestView, ServiceWorkerView
from ephios.core.views.settings import (
    CalendarSettingsView,
    InstanceSettingsView,
    NotificationSettingsView,
    PasswordChangeSettingsView,
    PersonalDataSettingsView,
)
from ephios.core.views.shift import (
    ShiftCreateView,
    ShiftDeleteView,
    ShiftStructureConfigurationFormView,
    ShiftUpdateView,
    SignupFlowConfigurationFormView,
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
    path("manifest.json", PWAManifestView.as_view(), name="pwa_manifest"),
    path("serviceworker.js", ServiceWorkerView.as_view(), name="pwa_serviceworker"),
    path("offline/", OfflineView.as_view(), name="pwa_offline"),
    path("healthcheck/", HealthCheckView.as_view(), name="healthcheck"),
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
        "events/<int:event_id>/form/signup-flow-config/<slug:slug>/",
        SignupFlowConfigurationFormView.as_view(),
        name="signup_flow_configuration_form",
    ),
    path(
        "events/<int:event_id>/form/shift-structure-config/<slug:slug>/",
        ShiftStructureConfigurationFormView.as_view(),
        name="shift_structure_configuration_form",
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
    path("settings/idp/", IdentityProviderListView.as_view(), name="settings_idp_list"),
    path("settings/idp/create/", IdentityProviderCreateView.as_view(), name="settings_idp_create"),
    path(
        "settings/idp/discovery/",
        IdentityProviderDiscoveryView.as_view(),
        name="settings_idp_discovery",
    ),
    path(
        "settings/idp/<int:pk>/edit/",
        IdentityProviderUpdateView.as_view(),
        name="settings_idp_edit",
    ),
    path(
        "settings/idp/<int:pk>/delete/",
        IdentityProviderDeleteView.as_view(),
        name="settings_idp_delete",
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
        "users/<int:pk>/password_revoke/",
        UserProfilePasswordTokenRevokationView.as_view(),
        name="userprofile_password_token_revoke",
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
    path("workinghours/own/", OwnWorkingHourView.as_view(), name="workinghours_own"),
    path(
        "workinghours/own/request/",
        WorkingHourRequestView.as_view(),
        name="workinghours_request",
    ),
    path("workinghours/", WorkingHourOverview.as_view(), name="workinghours_list"),
    path("workinghours/<int:pk>/edit/", WorkingHourUpdateView.as_view(), name="workinghours_edit"),
    path(
        "workinghours/<int:pk>/delete/", WorkingHourDeleteView.as_view(), name="workinghours_delete"
    ),
    path(
        "workinghours/user/<int:pk>/",
        UserProfileWorkingHourView.as_view(),
        name="workinghours_detail",
    ),
    path(
        "workinghours/user/<int:pk>/add/",
        WorkingHourCreateView.as_view(),
        name="workinghours_add",
    ),
    path("oidc/initiate/<int:provider>/", OIDCInitiateView.as_view(), name="oidc_initiate"),
    path("oidc/callback/", OIDCCallbackView.as_view(), name="oidc_callback"),
    path("oidc/logout/", OIDCLogoutView.as_view(), name="oidc_logout"),
    path("accounts/login/", OIDCLoginView.as_view(), name="oidc_login"),
    path("notifications/", NotificationListView.as_view(), name="notification_list"),
    path(
        "notifications/read/", NotificationMarkAllAsReadView.as_view(), name="notification_all_read"
    ),
    path("notifications/<int:pk>/", NotificationDetailView.as_view(), name="notification_detail"),
    path(
        "notifications/<int:pk>/read/",
        NotificationMarkAsReadView.as_view(),
        name="notification_read",
    ),
    path("media/ticket/<str:ticket>/", FileTicketView.as_view(), name="file_ticket"),
]
