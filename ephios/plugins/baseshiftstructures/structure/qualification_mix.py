from django import forms
from django.utils.translation import gettext_lazy as _

from ephios.core.models import Qualification
from ephios.plugins.baseshiftstructures.structure.group_common import (
    AbstractGroupBasedStructureConfigurationForm,
    QualificationRequirementForm,
)
from ephios.plugins.baseshiftstructures.structure.named_teams import BaseGroupBasedShiftStructure

QualificationRequirementFormset = forms.formset_factory(
    QualificationRequirementForm, can_delete=True, min_num=1, validate_min=1, extra=0
)


class QualificationMixConfigurationForm(AbstractGroupBasedStructureConfigurationForm):
    template_name = "baseshiftstructures/qualification_mix/configuration_form.html"
    qualification_requirements = forms.Field(
        label=_("Qualification Requirements"),
        widget=forms.HiddenInput,
        required=False,
    )
    formset_data_field_name = "qualification_requirements"
    formset_class = QualificationRequirementFormset

    @classmethod
    def format_formset_item(cls, item):
        if isinstance(item["qualification"], Qualification):
            qualification_name = str(item["qualification"])
        else:
            try:
                qualification_name = str(Qualification.objects.get(id=item["qualification"]))
            except Qualification.DoesNotExist:
                qualification_name = _("unknown")
        min_count, max_count = item.get("min_count"), item.get("max_count")
        if not max_count:
            return f"{qualification_name} ({min_count}+)"
        elif min_count == max_count:
            return f"{qualification_name} ({min_count})"
        else:
            return f"{qualification_name} ({min_count}-{max_count})"


class QualificationMixShiftStructure(BaseGroupBasedShiftStructure):
    slug = "qualification_mix"
    verbose_name = _("Qualification mix")
    description = _("require varying counts of different qualifications")
    shift_state_template_name = "baseshiftstructures/qualification_mix/fragment_state.html"
    configuration_form_class = QualificationMixConfigurationForm

    def get_shift_state_context_data(self, request, **kwargs):
        context_data = super().get_shift_state_context_data(request)
        return context_data
