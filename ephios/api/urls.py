from django.urls import include, path
from rest_framework import routers
from rest_framework.schemas import get_schema_view

from ephios.api.access.views import AccessTokenCreateView
from ephios.api.views.events import EventViewSet

router = routers.DefaultRouter()
router.register(r"events", EventViewSet)

app_name = "api"
urlpatterns = [
    path("", include(router.urls)),
    path(
        "schema/",
        get_schema_view(title="ephios", description="ephios API", version="1.0.0"),
        name="openapi-schema",
    ),
    path(
        "settings/api/token/create/",
        AccessTokenCreateView.as_view(),
        name="settings-authorized-token-create",
    ),
]
