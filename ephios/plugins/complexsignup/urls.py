from django.urls import include, path
from rest_framework import routers

from ephios.plugins.complexsignup.api import BuildingBlockViewSet
from ephios.plugins.complexsignup.views import BuildingBlockEditorView

router = routers.DefaultRouter()
router.register(r"buildingblocks", BuildingBlockViewSet)

app_name = "complexsignup"
urlpatterns = [
    path("settings/signup-blocks/", BuildingBlockEditorView.as_view(), name="blocks_editor"),
    path("api/", include(router.urls)),  # can we integrate this into the main router?
]
