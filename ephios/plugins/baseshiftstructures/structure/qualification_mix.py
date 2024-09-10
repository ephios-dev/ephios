import itertools
from functools import partial

from django import forms
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from ephios.core.models import AbstractParticipation, Qualification
from ephios.core.services.matching import Position, match_participants_to_positions, skill_level
from ephios.core.signup.flow.participant_validation import (
    ParticipantUnfitError,
    SignupDisallowedError,
)
from ephios.core.signup.participants import PlaceholderParticipant
from ephios.plugins.baseshiftstructures.structure.group_common import (
    AbstractGroupBasedStructureConfigurationForm,
    QualificationRequirementForm,
    format_min_max_count,
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

    def get_formset_class(self):
        return QualificationRequirementFormset

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
        return f"{format_min_max_count(min_count, max_count)} {qualification_name}"


class QualificationMixShiftStructure(BaseGroupBasedShiftStructure):
    slug = "qualification_mix"
    verbose_name = _("Qualification mix")
    description = _("Require varying counts of different qualifications.")
    shift_state_template_name = "baseshiftstructures/qualification_mix/fragment_state.html"
    configuration_form_class = QualificationMixConfigurationForm

    def check_qualifications(self, shift, participant, strict_mode=True):
        if not strict_mode:
            # check if the participant fulfills any of the requirements
            participant_skill = participant.collect_all_qualifications()
            for __, __, qualifications in self._requirements:
                if all(required_q in participant_skill for required_q in qualifications):
                    return
        else:
            # check if the participant can be matched into already confirmed participations
            confirmed_participants = [
                p.participant
                for p in shift.participations.all()
                if p.state == AbstractParticipation.States.CONFIRMED
            ]
            if participant in confirmed_participants:
                return
            positions = self._get_positions_for_matching(
                len(confirmed_participants) + 1
            )  # +1 for new participant
            matching_without = match_participants_to_positions(confirmed_participants, positions)
            matching_with = match_participants_to_positions(
                confirmed_participants + [participant], positions
            )
            if len(matching_with.pairings) > len(matching_without.pairings):
                return

        if (free := shift.get_signup_stats().free) and free > 0:
            raise ParticipantUnfitError(_("You are not qualified."))
        raise SignupDisallowedError(_("The maximum number of participants is reached."))

    def get_checkers(self):
        return super().get_checkers() + [
            partial(
                self.check_qualifications,
                strict_mode=not self.shift.signup_flow.uses_requested_state,
            )
        ]

    @cached_property
    def _requirements(self):
        requirements = []
        for requirement_idx, requirement in enumerate(
            self.configuration.qualification_requirements
        ):
            try:
                qualifications = {Qualification.objects.get(id=requirement["qualification"])}
            except Qualification.DoesNotExist:
                qualifications = set()
            requirements.append((str(requirement_idx), requirement, qualifications))
        # return requirements sorted by descending skill level
        return sorted(requirements, key=lambda r: skill_level(r[2]), reverse=True)

    def _get_positions_for_matching(self, number_of_participations: int):
        position_ids = itertools.count()
        positions = set()
        for requirement_id, requirement, qualifications in self._requirements:
            count = requirement["max_count"]
            if count is None:
                count = max(requirement["min_count"], number_of_participations)
            for i in range(count):
                positions.add(
                    Position(
                        f"{requirement_id}-{next(position_ids)}",
                        required_qualifications=qualifications,
                        preferred_by=set(),
                        designated_for=set(),
                        required=i < requirement["min_count"],
                    )
                )
        return positions

    def _could_sign_up_for_requirement(self, qualifications):
        try:
            extra_participant = PlaceholderParticipant(
                "Extra participant",
                qualifications,
                None,
                None,
            )
            self.check_qualifications(self.shift, extra_participant, strict_mode=True)
            return True
        except SignupDisallowedError:
            return False

    def get_shift_state_context_data(self, request, **kwargs):
        context_data = super().get_shift_state_context_data(request)
        # for displaying, match all requested and confirmed participations
        positive_participations = context_data["participations"]
        participants = {participation.participant for participation in positive_participations}
        positions = self._get_positions_for_matching(len(positive_participations))
        matching = match_participants_to_positions(participants, positions)
        matching.attach_participations(positive_participations)

        stats_per_group = self._get_signup_stats_per_group(positive_participations)
        requirements = []
        for requirement_id, requirement, qualifications in self._requirements:
            participations_for_requirement = [
                participation
                for participation, position in matching.participation_pairings
                if position.id.split("-")[0] == requirement_id
            ]
            requirement = {
                "qualifications": qualifications,
                "qualification_label": ", ".join(q.abbreviation for q in qualifications) or "",
                "min_count": requirement["min_count"],
                "max_count": requirement["max_count"],
                "min_max_count": format_min_max_count(
                    requirement["min_count"], requirement["max_count"]
                ),
                "has_free": self._could_sign_up_for_requirement(qualifications),
                "missing": stats_per_group[requirement_id].missing,
                "confirmed_count": len(
                    [
                        p
                        for p in participations_for_requirement
                        if p.state == AbstractParticipation.States.CONFIRMED
                    ]
                ),
                "participations": participations_for_requirement,
                "placeholder": list(
                    range(max(0, requirement["min_count"] - len(participations_for_requirement)))
                ),
            }
            requirements.append(requirement)

        context_data["requirements"] = requirements
        context_data["matching"] = matching
        return context_data

    def _get_signup_stats_per_group(self, participations):
        from ephios.core.signup.stats import SignupStats

        confirmed_participations = [
            participation
            for participation in participations
            if participation.state == AbstractParticipation.States.CONFIRMED
        ]

        participants = {participation.participant for participation in confirmed_participations}
        positions = self._get_positions_for_matching(len(confirmed_participations))
        matching = match_participants_to_positions(participants, positions)
        matching.attach_participations(confirmed_participations)

        requirement_stats = {}
        # confirmed influences missing, and missing needs to be calculated per
        # each requirement, so we need to iterate over all requirements
        for requirement_id, requirement, __ in self._requirements:
            confirmed_count = len(
                [
                    participation
                    for participation, position in matching.participation_pairings
                    if position.id.split("-")[0] == requirement_id
                ]
            )
            requirement_stats[requirement_id] = SignupStats(
                requested_count=0,
                confirmed_count=confirmed_count,
                missing=max(requirement["min_count"] - confirmed_count, 0),
                free=(
                    max(requirement["max_count"] - confirmed_count, 0)
                    if requirement["max_count"]
                    else None
                ),
                min_count=requirement["min_count"],
                max_count=requirement["max_count"],
            )

        # still got to deal with unpaired participants and all requested participations
        requested_count = len(
            [
                participation
                for participation in participations
                if participation.state == AbstractParticipation.States.REQUESTED
            ]
        )
        requirement_stats["unpaired"] = SignupStats.ZERO.replace(
            requested_count=requested_count, confirmed_count=len(matching.unpaired_participations)
        )
        return requirement_stats

    def get_participation_display(self):
        positive_participations = [
            p
            for p in self.shift.participations.all()
            if p.state in AbstractParticipation.States.REQUESTED_AND_CONFIRMED
        ]
        participants = {participation.participant for participation in positive_participations}
        positions = self._get_positions_for_matching(len(positive_participations))
        matching = match_participants_to_positions(participants, positions)
        matching.attach_participations(positive_participations)

        participation_display = []
        for participation, position in matching.participation_pairings:
            qualification_label = (
                ", ".join(q.abbreviation for q in position.required_qualifications) or "?"
            )
            participation_display.append(
                [
                    str(participation.participant),
                    qualification_label,
                ]
            )
        for position in matching.unpaired_positions:
            if position.required:
                qualification_label = (
                    ", ".join(q.abbreviation for q in position.required_qualifications) or "?"
                )
                participation_display.append(["", qualification_label])
        return participation_display
