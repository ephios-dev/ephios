from django.urls import path

from ephios.plugins.complexsignup.views import BuildingBlockEditorView, new_atomic_block_hx

app_name = "complexsignup"
urlpatterns = [
    path("settings/signup-blocks/", BuildingBlockEditorView.as_view(), name="blocks_editor"),
    path("settings/signup-blocks/new-atomic/", new_atomic_block_hx, name="blocks_atomic_create"),
]
