from django import forms
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from ephios.extra.mixins import CustomPermissionRequiredMixin
from ephios.plugins.complexsignup.models import BuildingBlock, BuildingBlockType


class BuildingBlockEditorView(CustomPermissionRequiredMixin, TemplateView):
    template_name = "complexsignup/htmx_editor.html"
    permission_required = "complexsignup:buildingblock_update"


class HtmxBuildingBlockForm(forms.ModelForm):
    class Meta:
        model = BuildingBlock
        fields = ["name", "allow_more"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": _("Name")}),
        }


def new_atomic_block_hx(request):
    block = BuildingBlock(block_type=BuildingBlockType.atomic)
    block_form = HtmxBuildingBlockForm(instance=block)
    return render(
        request,
        "complexsignup/partials/block_atomic.html",
        {"block_form": block_form},
    )
