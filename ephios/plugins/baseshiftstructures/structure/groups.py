import uuid

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django_select2.forms import Select2MultipleWidget

from ephios.core.models import AbstractParticipation, Qualification
from ephios.core.signup.disposition import BaseDispositionParticipationForm
from ephios.core.signup.participants import AbstractParticipant
from ephios.core.signup.structure.base import (
    BaseShiftStructure,
    BaseShiftStructureConfigurationForm,
)
from ephios.plugins.baseshiftstructures.structure.common import MinimumAgeConfigForm


def groups_participant_qualifies_for(groups, participant: AbstractParticipant):
    available_qualification_ids = set(q.id for q in participant.collect_all_qualifications())
    return [group for group in groups if group["qualification"] in available_qualification_ids]


class NamedGroupsDispositionParticipationForm(BaseDispositionParticipationForm):
    disposition_participation_template = "basesignup/group_based/fragment_participation.html"

    group = forms.ChoiceField(
        label=_("Section"),
        required=False,  # only required if participation is confirmed
        widget=forms.Select(
            attrs={"data-show-for-state": str(AbstractParticipation.States.CONFIRMED)}
        ),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        groups = self.shift.structure.configuration.groups
        qualified_groups = list(
            groups_participant_qualifies_for(
                groups,
                self.instance.participant,
            )
        )
        unqualified_groups = [group for group in groups if group not in qualified_groups]
        self.fields["group"].choices = [("", "---")]
        if qualified_groups:
            self.fields["group"].choices += [
                (
                    _("qualified"),
                    [(group["uuid"], group["title"]) for group in qualified_groups],
                )
            ]
        if unqualified_groups:
            self.fields["group"].choices += [
                (
                    _("unqualified"),
                    [(group["uuid"], group["title"]) for group in unqualified_groups],
                )
            ]
        if preferred_group_uuid := self.instance.data.get("preferred_group_uuid"):
            self.fields["group"].initial = preferred_group_uuid
            self.preferred_group = next(
                filter(lambda group: group["uuid"] == preferred_group_uuid, groups), None
            )
        if initial := self.instance.data.get("dispatched_group_uuid"):
            self.fields["group"].initial = initial

    def clean(self):
        super().clean()
        if (
            self.cleaned_data["state"] == AbstractParticipation.States.CONFIRMED
            and not self.cleaned_data["group"]
        ):
            self.add_error(
                "group",
                ValidationError(_("You must select a group when confirming a participation.")),
            )

    def save(self, commit=True):
        self.instance.data["dispatched_group_uuid"] = self.cleaned_data["group"]
        super().save(commit)


class NamedGroupForm(forms.Form):
    title = forms.CharField(label=_("Title"), required=True)
    qualification = forms.ModelChoiceField(
        label=_("Required Qualifications"),
        queryset=Qualification.objects.all(),
        widget=Select2MultipleWidget,
        required=False,
    )
    min_count = forms.IntegerField(label=_("min amount"), min_value=0, required=True)
    max_count = forms.IntegerField(label=_("max amount"), min_value=1, required=False)
    uuid = forms.CharField(widget=forms.HiddenInput, required=False)

    def clean_uuid(self):
        return self.cleaned_data.get("uuid") or uuid.uuid4()


NamedGroupsFormset = forms.formset_factory(
    NamedGroupForm, can_delete=True, min_num=1, validate_min=1, extra=0
)


class NamedGroupsConfigurationForm(MinimumAgeConfigForm, BaseShiftStructureConfigurationForm):
    pass


# TODO


class BaseGroupBasedShiftStructure(BaseShiftStructure):
    pass


class QualificationMixShiftStructure(BaseGroupBasedShiftStructure):
    slug = "qualification_mix"
    verbose_name = _("Qualification mix")
    description = _("require varying counts of different qualifications")


class NamedGroupsShiftStructure(BaseGroupBasedShiftStructure):
    slug = "named_groups"
    verbose_name = _("Named groups")
    description = _("define named groups of participants with different requirements")
    configuration_form_class = NamedGroupsConfigurationForm
