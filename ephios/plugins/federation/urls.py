from django.urls import path

from ephios.plugins.federation.views import (
    FederatedEventDetailView,
    FederatedUserShiftActionView,
    FederationOAuthView,
    IncomingSharedEventListView,
    RedeemFederationInviteCodeView,
    SharedEventListView,
)

app_name = "federation"
urlpatterns = [
    path(
        "events/shared/",
        IncomingSharedEventListView.as_view(),
        name="incoming_shared_event_list_view",
    ),
    path("events/shared/<int:pk>/", FederatedEventDetailView.as_view(), name="event_detail"),
    path(
        "shifts/shared/<int:pk>/signup/",
        FederatedUserShiftActionView.as_view(),
        name="shift_signup",
    ),
    path(
        "api/federation/events/",
        SharedEventListView.as_view(),
        name="outgoing_shared_event_list_view",
    ),
    path(
        "api/federation/oauth-callback/",
        FederationOAuthView.as_view(),
        name="federation_oauth_callback",
    ),
    path(
        "api/federation/setup/", RedeemFederationInviteCodeView.as_view(), name="reedem_invite_code"
    ),
]
