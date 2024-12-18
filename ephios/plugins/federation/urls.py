from django.urls import path

from ephios.plugins.federation.views import api, frontend

app_name = "federation"

urlpatterns = [
    path(
        "events/external/",
        frontend.ExternalEventListView.as_view(),
        name="external_event_list",
    ),
    path(
        "events/shared/<int:pk>/<int:guest>/",
        frontend.FederatedEventDetailView.as_view(),
        name="event_detail",
    ),
    path(
        "shifts/shared/<int:pk>/<int:guest>/signup/",
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
        "settings/federation/hosts/<int:pk>/delete/",
        frontend.FederatedHostDeleteView.as_view(),
        name="delete_host",
    ),
    path(
        "settings/federation/guests/add/",
        frontend.CreateInviteCodeView.as_view(),
        name="create_invite_code",
    ),
    path(
        "settings/federation/guests/<int:pk>/delete/",
        frontend.FederatedGuestDeleteView.as_view(),
        name="delete_guest",
    ),
    path(
        "settings/federation/invite/<int:pk>/",
        frontend.InviteCodeRevealView.as_view(),
        name="reveal_invite_code",
    ),
    path(
        "api/federation/events/",
        api.SharedEventListView.as_view(),
        name="shared_event_list_view",
    ),
    path(
        "api/federation/oauth-callback/",
        api.FederationOAuthView.as_view(),
        name="oauth_callback",
    ),
    path(
        "api/federation/setup/",
        api.RedeemInviteCodeView.as_view(),
        name="redeem_invite_code",
    ),
    path(
        "api/federation/guest/delete/",
        api.FederatedGuestDeleteView.as_view(),
        name="api_delete_guest",
    ),
]
