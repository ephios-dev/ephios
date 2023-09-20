import json

from csp.decorators import csp_exempt
from django import forms
from django.contrib import messages
from django.db import transaction
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView

from ephios.core.models import Qualification
from ephios.extra.json import CustomJSONEncoder
from ephios.extra.mixins import CustomPermissionRequiredMixin
from ephios.plugins.complexsignup.models import BuildingBlock
from ephios.plugins.complexsignup.serializers import BuildingBlockSerializer


class BuildingBlocksForm(forms.Form):
    blocks = forms.JSONField(
        widget=forms.HiddenInput(
            attrs={
                ":value": "JSON.stringify(blocks)",
            }
        ),
        encoder=CustomJSONEncoder,
        required=False,
    )

    def save(self):
        serializer = BuildingBlockSerializer(
            instance=BuildingBlock.objects.all(),
            many=True,
            data=self.cleaned_data["blocks"],
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()


class BuildingBlockEditorView(CustomPermissionRequiredMixin, FormView):
    template_name = "complexsignup/vue_editor.html"
    permission_required = "complexsignup:buildingblock_update"
    form_class = BuildingBlocksForm
    success_url = reverse_lazy("complexsignup:blocks_editor")

    def get_initial(self):
        return {"blocks": BuildingBlockSerializer(BuildingBlock.objects.all(), many=True).data}

    def form_valid(self, form):
        try:
            with transaction.atomic():
                form.save()
        except Exception as e:
            messages.error(self.request, _("Failed to save building blocks."))
            raise e
            # return self.form_invalid(form)
        messages.success(self.request, _("Saved blocks."))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qualifications = Qualification.objects.all()
        context["qualifications"] = qualifications
        context["qualifications_json"] = json.dumps(
            {
                q.id: {
                    "title": q.title,
                    "abbreviation": q.abbreviation,
                }
                for q in qualifications
            }
        )
        return context

    @classmethod
    def as_view(cls, **initkwargs):
        return csp_exempt(super().as_view(**initkwargs))
