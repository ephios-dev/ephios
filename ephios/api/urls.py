from django.conf import settings
from django.urls import include, path
from oauth2_provider import views as oauth2_views
from rest_framework import routers
from rest_framework.schemas import get_schema_view

from ephios.api.access.views import (
    AccessTokenCreateView,
    AccessTokenRevealView,
    AccessTokenRevokeView,
    AccessTokensListView,
    AllUserApplicationList,
    ApplicationDelete,
)
from ephios.api.views.events import EventViewSet
from ephios.api.views.users import UserProfileMeView
from ephios.extra.permissions import staff_required

router = routers.DefaultRouter()
router.register(r"events", EventViewSet)

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
                    staff_required(AllUserApplicationList.as_view()),
                    name="settings-oauth-app-list",
                ),
                path(
                    "applications/register/",
                    staff_required(oauth2_views.ApplicationRegistration.as_view()),
                    name="settings-oauth-app-register",
                ),
                path(
                    "applications/<int:pk>/",
                    staff_required(oauth2_views.ApplicationDetail.as_view()),
                    name="settings-oauth-app-detail",
                ),
                path(
                    "applications/<int:pk>/delete/",
                    staff_required(ApplicationDelete.as_view()),
                    name="settings-oauth-app-delete",
                ),
                path(
                    "applications/<int:pk>/update/",
                    staff_required(oauth2_views.ApplicationUpdate.as_view()),
                    name="settings-oauth-app-update",
                ),
            ]
        ),
    ),
    path(
        "schema/",
        get_schema_view(
            title="ephios",
            description="ephios API",
            version=settings.EPHIOS_VERSION,
            url=settings.GET_SITE_URL(),
        ),
        name="openapi-schema",
    ),
    path("", include(router.urls)),
]
