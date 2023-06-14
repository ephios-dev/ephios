from django.urls import path

from ephios.plugins.federation.views import api, frontend

app_name = "federation"
urlpatterns = [
    path(
        "events/shared/",
        frontend.IncomingSharedEventListView.as_view(),
        name="incoming_shared_event_list_view",
    ),
    path(
        "events/shared/<int:pk>/", frontend.FederatedEventDetailView.as_view(), name="event_detail"
    ),
    path(
        "shifts/shared/<int:pk>/signup/",
        frontend.FederatedUserShiftActionView.as_view(),
        name="shift_signup",
    ),
    path("settings/federation/", frontend.FederationSettingsView.as_view(), name="settings"),
    path(
        "settings/federation/hosts/add/",
        frontend.RedeemInviteCodeView.as_view(),
        name="frontend_redeem_invite_code",
    ),
    path(
        "settings/federation/guests/add/",
        frontend.CreateInviteCodeView.as_view(),
        name="create_invite_code",
    ),
    path(
        "api/federation/events/",
        api.SharedEventListView.as_view(),
        name="outgoing_shared_event_list_view",
    ),
    path(
        "api/federation/oauth-callback/",
        frontend.FederationOAuthView.as_view(),
        name="federation_oauth_callback",
    ),
    path(
        "api/federation/setup/",
        api.RedeemFederationInviteCodeView.as_view(),
        name="redeem_invite_code",
    ),
]
