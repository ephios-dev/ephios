from django.urls import include, path
from rest_framework import routers

# Serializers define the API representation.
from ephios.api.events import EventViewSet

# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()
router.register(r"events", EventViewSet)

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path(
        "v<int:version>/",
        include(
            [
                path("", include(router.urls)),
                path("auth/", include("rest_framework.urls", namespace="rest_framework")),
            ]
        ),
    )
]
