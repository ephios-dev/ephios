from django import forms
from django.utils.translation import gettext_lazy as _
from django_select2.forms import ModelSelect2Widget

from ephios.core.signup.forms import SignupConfigurationForm
from ephios.core.signup.structure.base import BaseShiftStructure
from ephios.plugins.baseshiftstructures.structure.common import MinimumAgeMixin
from ephios.plugins.complexsignup.models import BuildingBlock


class ComplexConfigurationForm(SignupConfigurationForm):
    building_block = forms.ModelChoiceField(
        widget=ModelSelect2Widget(
            model=BuildingBlock,
            search_fields=["name"],
        ),
        queryset=BuildingBlock.objects.all(),
    )

    template_name = "complexsignup/configuration_form.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ComplexShiftStructure(
    MinimumAgeMixin,
    BaseShiftStructure,
):
    slug = "complex"
    verbose_name = _("Preconfigured Structure")
    description = _("Use preconfigured elements to build a custom structure.")
    shift_state_template_name = "complexsignup/shift_state.html"
    configuration_form_class = ComplexConfigurationForm

    def get_shift_state_context_data(self, request, **kwargs):
        """
        Additionally to the context of the event detail view, provide context for rendering `shift_state_template_name`.
        """
        kwargs = super().get_shift_state_context_data(request, **kwargs)
        kwargs["main_block"] = BuildingBlock.objects.filter(
            id=self.configuration.building_block
        ).first()
        return kwargs
