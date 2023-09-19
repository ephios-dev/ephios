from django.urls import path

from ephios.plugins.complexsignup.views import BuildingBlockEditorView

app_name = "complexsignup"
urlpatterns = [
    path("settings/signup-blocks/", BuildingBlockEditorView.as_view(), name="blocks_editor"),
]
