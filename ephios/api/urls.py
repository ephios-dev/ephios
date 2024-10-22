from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerSplitView
from oauth2_provider import views as oauth2_views
from rest_framework import routers

from ephios.api.access.views import (
    AccessTokenCreateView,
    AccessTokenRevealView,
    AccessTokenRevokeView,
    AccessTokensListView,
    AllUserApplicationList,
    ApplicationDelete,
    ApplicationDetail,
    ApplicationUpdate,
)
from ephios.api.views.events import EventViewSet, ShiftViewSet
from ephios.api.views.users import (
    UserByMailView,
    UserParticipationView,
    UserProfileMeView,
    UserViewSet,
)
from ephios.extra.permissions import staff_required

router = routers.DefaultRouter()
router.register(r"events", EventViewSet)
router.register(r"shifts", ShiftViewSet)
router.register(r"users", UserViewSet)
router.register(r"users/by_email", UserByMailView, basename="user-by-email")
router.register(
    r"users/(?P<user>[\d]+)/participations", UserParticipationView, basename="user-participations"
)

app_name = "api"
urlpatterns = [
    path("users/me/", UserProfileMeView.as_view(), name="user-profile-me"),
    path(
        "settings/",
        include(
            [
                # Token management views
                path(
                    "token/",
                    AccessTokensListView.as_view(),
                    name="settings-access-token-list",
                ),
                path(
                    "token/create/",
                    AccessTokenCreateView.as_view(),
                    name="settings-access-token-create",
                ),
                path(
                    "token/reveal/<int:pk>/",
                    AccessTokenRevealView.as_view(),
                    name="settings-access-token-reveal",
                ),
                path(
                    "token/revoke/",
                    AccessTokenRevokeView.as_view(),
                    name="settings-access-token-revoke",
                ),
                # Application management views
                path(
                    "applications/",
                    AllUserApplicationList.as_view(),
                    name="settings-oauth-app-list",
                ),
                path(
                    "applications/register/",
                    staff_required(oauth2_views.ApplicationRegistration.as_view()),
                    name="settings-oauth-app-register",
                ),
                path(
                    "applications/<int:pk>/",
                    ApplicationDetail.as_view(),
                    name="settings-oauth-app-detail",
                ),
                path(
                    "applications/<int:pk>/delete/",
                    ApplicationDelete.as_view(),
                    name="settings-oauth-app-delete",
                ),
                path(
                    "applications/<int:pk>/update/",
                    ApplicationUpdate.as_view(),
                    name="settings-oauth-app-update",
                ),
            ]
        ),
    ),
    path(
        "schema/",
        SpectacularAPIView.as_view(),
        name="openapi-schema",
    ),
    path(
        "schema/swagger-ui/",
        SpectacularSwaggerSplitView.as_view(url_name="openapi-schema"),
        name="swagger-ui",
    ),
    path("", include(router.urls)),
]
