import itertools

from django import forms
from django.utils.translation import gettext_lazy as _

from ephios.core.models import AbstractParticipation, Qualification
from ephios.core.services.matching import Position, match_participants_to_positions
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

    def _get_positions_for_matching(self, number_of_participations: int):
        position_ids = itertools.count()
        positions = set()
        for requirement in self.configuration.qualification_requirements:
            try:
                qualifications = {Qualification.objects.get(id=requirement["qualification"])}
            except Qualification.DoesNotExist:
                qualifications = set()
            count = (
                max if (max := requirement["max_count"]) is not None else number_of_participations
            )
            for i in range(count):
                positions.add(
                    Position(
                        next(position_ids),
                        required_qualifications=qualifications,
                        preferred_by=set(),
                        required=i < requirement["min_count"],
                    )
                )
        return positions

    def get_shift_state_context_data(self, request, **kwargs):
        context_data = super().get_shift_state_context_data(request)
        # for displaying, match all requested and confirmed participations
        positive_participations = [
            participation
            for participation in context_data["participations"]
            if participation.state
            in {AbstractParticipation.States.CONFIRMED, AbstractParticipation.States.REQUESTED}
        ]
        participants = {participation.participant for participation in positive_participations}
        positions = self._get_positions_for_matching(len(positive_participations))
        matching = match_participants_to_positions(participants, positions)
        matching.attach_participations(positive_participations)
        context_data["matching"] = matching
        return context_data
