from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django_select2.forms import Select2Widget

from ephios.core.models import Qualification
from ephios.core.signup.forms import SignupConfigurationForm
from ephios.core.signup.structure.base import BaseShiftStructure
from ephios.plugins.baseshiftstructures.structure.common import MinimumAgeConfigForm


def format_min_max_count(min_count, max_count):
    if not max_count:
        return f"{min_count}+"
    if min_count == max_count:
        return f"{min_count}"
    return f"{min_count}-{max_count}"


class BaseGroupBasedShiftStructure(BaseShiftStructure):

    def get_signup_stats(self):
        from ephios.core.signup.stats import SignupStats

        participations = list(self.shift.participations.all())
        return SignupStats.reduce(self._get_signup_stats_per_group(participations).values())

    def _get_signup_stats_per_group(self, participations):
        raise NotImplementedError


class AbstractGroupBasedStructureConfigurationForm(MinimumAgeConfigForm, SignupConfigurationForm):
    formset_data_field_name = None

    def get_formset_class(self):
        raise NotImplementedError

    def _clean_formset_data(self):
        if not self.formset.is_valid():
            raise ValidationError(
                _("{field_label} aren't configured correctly.").format(
                    field_label=self.fields[self.formset_data_field_name].label
                )
            )
        data = [
            {key: value for key, value in cleaned_data.items() if key != "DELETE"}
            for cleaned_data in self.formset.cleaned_data
            if cleaned_data and not cleaned_data.get("DELETE")
        ]
        return data

    def __init__(self, data=None, **kwargs):
        super().__init__(data, **kwargs)
        self.formset = self.get_formset_class()(
            data=data,
            initial=self.initial.get(self.formset_data_field_name, []),
            prefix=self.formset_data_field_name,
        )
        setattr(self, f"clean_{self.formset_data_field_name}", self._clean_formset_data)

    @classmethod
    def format_formset_item(cls, item):
        raise NotImplementedError

    @classmethod
    def _format_formset_data_field(cls, value):
        return ", ".join(cls.format_formset_item(item) for item in value)

    def __init_subclass__(cls):
        super().__init_subclass__()
        setattr(cls, f"format_{cls.formset_data_field_name}", cls._format_formset_data_field)


class QualificationRequirementForm(forms.Form):
    qualification = forms.ModelChoiceField(
        label=_("Required Qualification"),
        queryset=Qualification.objects.all(),
        widget=Select2Widget,
        required=False,
    )
    min_count = forms.IntegerField(label=_("min amount"), min_value=0, required=True)
    max_count = forms.IntegerField(label=_("max amount"), min_value=1, required=False)

    def clean_max_count(self):
        if (
            self.cleaned_data["max_count"]
            and (min_count := self.cleaned_data.get("min_count"))
            and self.cleaned_data["max_count"] < min_count
        ):
            raise ValidationError(_("Max count must not be smaller than min count."))
        return self.cleaned_data["max_count"]
