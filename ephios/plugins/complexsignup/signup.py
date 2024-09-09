import itertools
from functools import cached_property
from typing import Iterator

from django import forms
from django.utils.translation import gettext_lazy as _
from django_select2.forms import ModelSelect2Widget

from ephios.core.models import AbstractParticipation
from ephios.core.services.matching import Matching, Position, match_participants_to_positions
from ephios.core.signup.forms import SignupConfigurationForm
from ephios.core.signup.stats import SignupStats
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

    def _match(self, participations):
        confirmed_participations = [
            participation
            for participation in participations
            if participation.state == AbstractParticipation.States.CONFIRMED
        ]
        participants = {participation.participant for participation in confirmed_participations}
        all_positions, structure = convert_blocks_to_positions(self._base_blocks, len(participants))
        matching = match_participants_to_positions(participants, all_positions)
        matching.attach_participations(confirmed_participations)

        # let's work up the blocks again, but now with matching
        all_positions, structure = convert_blocks_to_positions(
            self._base_blocks, len(participants), matching=matching
        )
        # we just have to add unpaired matches to the full stats
        signup_stats = structure["signup_stats"] + SignupStats.ZERO.replace(
            requested_count=len(
                [
                    p
                    for p in matching.unpaired_participations
                    if p.state == AbstractParticipation.States.REQUESTED
                ]
            ),
            confirmed_count=len(
                [
                    p
                    for p in matching.unpaired_participations
                    if p.state == AbstractParticipation.States.CONFIRMED
                ]
            ),
        )
        return matching, structure, signup_stats

    @cached_property
    def _base_blocks(self):
        # for now, we only support one base block
        return [BuildingBlock.objects.filter(id=self.configuration.building_block).first()]

    def get_shift_state_context_data(self, request, **kwargs):
        """
        Additionally to the context of the event detail view, provide context for rendering `shift_state_template_name`.
        """
        kwargs = super().get_shift_state_context_data(request, **kwargs)
        participations = kwargs["participations"]
        matching, structure, stats = self._match(participations)
        kwargs["matching"] = matching
        kwargs["structure"] = structure
        return kwargs

    def get_signup_stats(self) -> "SignupStats":
        participations = list(self.shift.participations.all())
        matching, structure, stats = self._match(participations)
        return stats


def _search_block(
    block: BuildingBlock,
    path: str,
    level: int,
    required_qualifications: set,
    path_optional: bool,
    number_of_participants: int,
    opt_counter: Iterator,
    matching: Matching,
):
    required_here = set(required_qualifications)
    for requirement in block.qualification_requirements.filter(everyone=True):
        # at least one is not supported
        required_here |= set(requirement.qualifications.all())

    all_positions = []
    structure = {
        "is_composite": block.is_composite(),
        "positions": [],
        "participations": [],
        "sub_blocks": [],
        "path": path,
        "level": level,
        "optional": path_optional,
        "name": block.name,
        "qualification_label": ", ".join(q.abbreviation for q in required_here),
    }
    signup_stats = SignupStats.ZERO
    if block.is_composite():
        for composition in block.sub_blocks.through.objects.filter(composite_block=block):
            positions, sub_structure = _search_block(
                block=composition.sub_block,
                path=f"{path}{composition.id}-",
                level=level + 1,
                required_qualifications=required_here,
                path_optional=path_optional or composition.optional,
                opt_counter=opt_counter,
                number_of_participants=number_of_participants,
                matching=matching,
            )
            signup_stats += sub_structure["signup_stats"]
            all_positions.extend(positions)
            structure["sub_blocks"].append(sub_structure)
    else:
        for block_position in block.positions.all():
            match_id = f"{path}{block.uuid}-{block_position.id}"
            label = block_position.label or ", ".join(
                q.abbreviation for q in block_position.qualifications.all()
            )
            required = not (block_position.optional or path_optional)
            p = Position(
                id=match_id,
                required_qualifications=required_here | set(block_position.qualifications.all()),
                preferred_by=set(),
                required=required,
                label=label,
            )
            participation = matching.participation_for_position(match_id) if matching else None
            signup_stats += SignupStats.ZERO.replace(
                min_count=int(required),
                max_count=1,
                missing=bool(required and not participation),
                free=bool(participation is None),
                requested_count=bool(
                    participation and participation.state == AbstractParticipation.States.REQUESTED
                ),
                confirmed_count=bool(
                    participation and participation.state == AbstractParticipation.States.CONFIRMED
                ),
            )
            all_positions.append(p)
            structure["positions"].append(p)
            structure["participations"].append(participation)
            if block.allow_more:
                for _ in range(number_of_participants):
                    opt_match_id = f"{match_id}-{next(opt_counter)}"
                    p = Position(
                        id=opt_match_id,
                        required_qualifications=required_here
                        | set(block_position.qualifications.all()),
                        preferred_by=set(),
                        required=False,  # allow_more -> always optional
                        label=label,
                    )
                    participation = (
                        matching.participation_for_position(opt_match_id) if matching else None
                    )
                    signup_stats += SignupStats.ZERO.replace(
                        min_count=0,
                        max_count=None,  # allow_more -> always free
                        missing=0,
                        free=None,
                        requested_count=bool(
                            participation
                            and participation.state == AbstractParticipation.States.REQUESTED
                        ),
                        confirmed_count=bool(
                            participation
                            and participation.state == AbstractParticipation.States.CONFIRMED
                        ),
                    )
                    all_positions.append(p)
                    structure["positions"].append(p)
                    structure["participations"].append(participation)
    structure["signup_stats"] = signup_stats
    return all_positions, structure


def convert_blocks_to_positions(starting_blocks, number_of_participants, matching=None):
    """
    If a matching is provided, the signup stats will have correct participation counts
    """
    root_path = "root-"
    all_positions = []
    structure = {
        "is_composite": True,  # root block is "virtual" and always composite
        "positions": [],
        "position_match_ids": [],
        "sub_blocks": [],
        "path": root_path,
        "optional": False,
        "level": 0,
        "name": "ROOT",
        "qualification_label": "",
    }
    opt_counter = itertools.count()
    for block in starting_blocks:
        positions, sub_structure = _search_block(
            block,
            path=root_path,
            level=1,
            path_optional=False,
            required_qualifications=set(),
            number_of_participants=number_of_participants,
            opt_counter=opt_counter,
            matching=matching,
        )
        all_positions.extend(positions)
        structure["sub_blocks"].append(sub_structure)
    structure["signup_stats"] = SignupStats.reduce(
        [s["signup_stats"] for s in structure["sub_blocks"]]
    )
    return all_positions, structure
