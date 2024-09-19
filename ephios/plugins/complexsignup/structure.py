import itertools
import logging
from collections import defaultdict
from functools import cached_property, partial
from operator import attrgetter
from typing import Optional

from django import forms
from django.utils.translation import gettext_lazy as _
from django_select2.forms import ModelSelect2Widget

from ephios.core.models import AbstractParticipation
from ephios.core.services.matching import Matching, Position, match_participants_to_positions
from ephios.core.signup.disposition import BaseDispositionParticipationForm
from ephios.core.signup.flow.participant_validation import (
    ParticipantUnfitError,
    SignupDisallowedError,
)
from ephios.core.signup.forms import BaseSignupForm, SignupConfigurationForm
from ephios.core.signup.participants import AbstractParticipant
from ephios.core.signup.stats import SignupStats
from ephios.core.signup.structure.base import BaseShiftStructure
from ephios.plugins.baseshiftstructures.structure.common import MinimumAgeMixin
from ephios.plugins.complexsignup.models import BuildingBlock

logger = logging.getLogger(__name__)


def atomic_block_participant_qualifies_for(structure, participant: AbstractParticipant):
    available_qualification_ids = set(q.id for q in participant.collect_all_qualifications())
    return [
        block
        for block in iter_atomic_blocks(structure)
        if block["qualification_ids"] <= available_qualification_ids
        and any(
            {q.id for q in position.required_qualifications} <= available_qualification_ids
            for position in block["positions"]
        )
    ]


def _build_human_path(structure):
    return " » ".join(
        [
            *[s["display"] for s in reversed(structure["parents"])],
            f"{structure['display']} #{structure['number']}",
        ]
    )


class ComplexDispositionParticipationForm(BaseDispositionParticipationForm):
    disposition_participation_template = "complexsignup/fragment_participation.html"
    unit_path = forms.ChoiceField(
        label=_("Unit"),
        required=False,
        widget=forms.Select(
            attrs={"data-show-for-state": str(AbstractParticipation.States.CONFIRMED)}
        ),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        complex_structure = self.shift.structure
        complex_structure._assume_cache()

        qualified_blocks = atomic_block_participant_qualifies_for(
            complex_structure._structure, self.instance.participant
        )
        unqualified_blocks = [
            b for b in iter_atomic_blocks(complex_structure._structure) if b not in qualified_blocks
        ]

        self.fields["unit_path"].choices = [("", _("auto"))]
        if qualified_blocks:
            self.fields["unit_path"].choices += [
                (
                    _("qualified"),
                    [(b["path"], _build_human_path(b)) for b in qualified_blocks],
                )
            ]
        if unqualified_blocks:
            self.fields["unit_path"].choices += [
                (
                    _("unqualified"),
                    [(b["path"], _build_human_path(b)) for b in unqualified_blocks],
                )
            ]
        if preferred_unit_path := self.instance.structure_data.get("preferred_unit_path"):
            try:
                preferred_block = next(
                    filter(
                        lambda b: b["path"] == preferred_unit_path,
                        iter_atomic_blocks(complex_structure._structure),
                    )
                )
                self.preferred_unit_name = _build_human_path(preferred_block)
            except StopIteration:
                pass  # preferred block not found
        if initial := self.instance.structure_data.get("dispatched_unit_path"):
            self.fields["unit_path"].initial = initial

    def save(self, commit=True):
        self.instance.structure_data["dispatched_unit_path"] = self.cleaned_data["unit_path"]
        super().save(commit)


class ComplexSignupForm(BaseSignupForm):
    preferred_unit_path = forms.ChoiceField(
        label=_("Preferred Unit"),
        widget=forms.RadioSelect,
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["preferred_unit_path"].initial = self.instance.structure_data.get(
            "preferred_unit_path"
        )
        self.fields["preferred_unit_path"].required = (
            self.data.get("signup_choice") == "sign_up"
            and self.shift.structure.configuration.choose_preferred_unit
        )
        complex_structure = self.shift.structure
        complex_structure._assume_cache()
        self.fields["preferred_unit_path"].choices = [
            (b["path"], _build_human_path(b))
            for b in self.blocks_participant_qualifies_for(complex_structure._structure)
        ]
        unqualified_blocks = [
            b
            for b in iter_atomic_blocks(complex_structure._structure)
            if b not in self.blocks_participant_qualifies_for(complex_structure._structure)
        ]
        if unqualified_blocks:
            self.fields["preferred_unit_path"].help_text = _(
                "You don't qualify for {blocks}."
            ).format(blocks=", ".join(set(str(b["name"]) for b in unqualified_blocks)))

    def save(self, commit=True):
        self.instance.structure_data["preferred_unit_path"] = self.cleaned_data[
            "preferred_unit_path"
        ]
        return super().save(commit)

    def blocks_participant_qualifies_for(self, structure):
        return atomic_block_participant_qualifies_for(structure, self.participant)


class ComplexConfigurationForm(SignupConfigurationForm):
    building_block = forms.ModelChoiceField(
        widget=ModelSelect2Widget(
            model=BuildingBlock,
            search_fields=["name__icontains"],
        ),
        queryset=BuildingBlock.objects.all(),
    )
    choose_preferred_unit = forms.BooleanField(
        label=_("Participants must provide a preferred unit"),
        help_text=_("Participants will be asked during signup."),
        widget=forms.CheckboxInput,
        required=False,
        initial=False,
    )

    template_name = "complexsignup/configuration_form.html"


class ComplexShiftStructure(
    MinimumAgeMixin,
    BaseShiftStructure,
):
    slug = "complex"
    verbose_name = _("Preconfigured Structure (experimental)")
    description = _("Use preconfigured elements to build a custom structure.")
    shift_state_template_name = "complexsignup/shift_state.html"
    configuration_form_class = ComplexConfigurationForm
    disposition_participation_form_class = ComplexDispositionParticipationForm
    signup_form_class = ComplexSignupForm

    def _match(self, participations):
        participants = [participation.participant for participation in participations]
        confirmed_participants = [
            participation.participant
            for participation in participations
            if participation.state == AbstractParticipation.States.CONFIRMED
        ]
        all_positions, structure = convert_blocks_to_positions(self._base_blocks, participations)
        matching = match_participants_to_positions(
            participants, all_positions, confirmed_participants=confirmed_participants
        )
        matching.attach_participations(participations)

        # let's work up the blocks again, but now with matching
        all_positions, structure = convert_blocks_to_positions(
            self._base_blocks, participations, matching=matching
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
        return matching, all_positions, structure, signup_stats

    @cached_property
    def _base_blocks(self):
        # for now, we only support one base block
        qs = BuildingBlock.objects.all()
        return list(qs.filter(id=self.configuration.building_block))

    def _assume_cache(self):
        if not hasattr(self, "_cached_work"):
            participations = [
                p
                for p in sorted(
                    self.shift.participations.all(), key=attrgetter("state"), reverse=True
                )
                if p.state
                in {AbstractParticipation.States.REQUESTED, AbstractParticipation.States.CONFIRMED}
            ]
            self._matching, self._all_positions, self._structure, self._signup_stats = self._match(
                participations
            )
            self._cached_work = True

    def get_shift_state_context_data(self, request, **kwargs):
        """
        Additionally to the context of the event detail view, provide context for rendering `shift_state_template_name`.
        """
        kwargs = super().get_shift_state_context_data(request, **kwargs)
        self._assume_cache()
        kwargs["matching"] = self._matching
        kwargs["structure"] = self._structure
        return kwargs

    def get_signup_stats(self) -> "SignupStats":
        self._assume_cache()
        return self._signup_stats

    def check_qualifications(self, shift, participant, strict_mode=True):
        confirmed_participations = [
            p
            for p in shift.participations.all()
            if p.state == AbstractParticipation.States.CONFIRMED
        ]
        self._assume_cache()

        if not strict_mode:
            # check if the participant fulfills any of the requirements
            if atomic_block_participant_qualifies_for(self._structure, participant):
                return
        else:
            # check if the participant can be matched into already confirmed participations
            confirmed_participants = [p.participant for p in confirmed_participations]
            if participant in confirmed_participants:
                return
            matching_without = match_participants_to_positions(
                confirmed_participants, self._all_positions
            )
            matching_with = match_participants_to_positions(
                confirmed_participants + [participant], self._all_positions
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

    def get_participation_display(self):
        self._assume_cache()
        participation_display = []
        for block in iter_atomic_blocks(self._structure):
            for position, participation in zip(
                block["positions"],
                block["participations"],
            ):
                if not position.required:
                    continue
                qualification_label = (
                    ", ".join(q.abbreviation for q in position.required_qualifications) or "?"
                )
                participation_display.append(
                    [
                        str(participation.participant) if participation else "",
                        qualification_label,
                        f"{block['display']} #{block['number']}",
                    ]
                )
        return participation_display


def _search_block(
    block: BuildingBlock,
    path: str,
    level: int,
    required_qualifications: set,
    path_optional: bool,
    participations: list[AbstractParticipation],
    opt_counter,
    matching: Matching,
    parents: list,
    composed_label: Optional[str] = None,
):  # pylint: disable=too-many-locals
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
        "label": composed_label,
        "display": composed_label or block.name,
        "number": next(opt_counter[block.name]),
        "qualification_label": ", ".join(q.abbreviation for q in required_here),
        "qualification_ids": {q.id for q in required_here},
        "parents": parents,
        "signup_stats": SignupStats.ZERO,
    }
    if block.is_composite():
        for composition in block.sub_blocks.through.objects.filter(
            composite_block=block
        ).prefetch_related(
            "sub_block__positions__qualifications",
            "sub_block__qualification_requirements__qualifications",
        ):
            positions, sub_structure = _search_block(
                block=composition.sub_block,
                path=f"{path}{composition.id}-",
                level=level + 1,
                required_qualifications=required_here,
                path_optional=path_optional or composition.optional,
                opt_counter=opt_counter,
                participations=participations,
                matching=matching,
                parents=[structure, *parents],
                composed_label=composition.label,
            )
            structure["signup_stats"] += sub_structure["signup_stats"]
            all_positions.extend(positions)
            structure["sub_blocks"].append(sub_structure)
    else:
        _build_atomic_block_structure(
            all_positions,
            block,
            matching,
            opt_counter,
            participations,
            path,
            path_optional,
            required_here,
            structure,
        )
    return all_positions, structure


def _build_atomic_block_structure(
    all_positions,
    block,
    matching,
    opt_counter,
    participations,
    path,
    path_optional,
    required_here,
    structure,
):  # pylint: disable=too-many-locals
    designated_for = {
        p.participant
        for p in participations
        if p.structure_data.get("dispatched_unit_path") == path
    }
    preferred_by = {
        p.participant for p in participations if p.structure_data.get("preferred_unit_path") == path
    }
    for block_position in block.positions.all():
        match_id = _build_position_id(block, block_position.id, path)
        label = block_position.label or ", ".join(
            q.abbreviation for q in block_position.qualifications.all()
        )
        required = not (block_position.optional or path_optional)
        p = Position(
            id=match_id,
            required_qualifications=required_here | set(block_position.qualifications.all()),
            designated_for=designated_for,
            preferred_by=preferred_by,
            required=required,
            label=label,
            aux_score=1,
        )
        participation = matching.participation_for_position(match_id) if matching else None
        structure["signup_stats"] += SignupStats.ZERO.replace(
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

    # build derivative positions for "allow_more" participants
    allow_more_count = int(block.allow_more) * (
        len(participations) + 1
    )  # 1 extra in case of signup matching check
    for _ in range(allow_more_count):
        opt_match_id = _build_position_id(block, next(opt_counter[str(block.id)]), path)
        p = Position(
            id=opt_match_id,
            required_qualifications=required_here,
            preferred_by=preferred_by,
            designated_for=designated_for,
            aux_score=0,
            required=False,  # allow_more -> always optional
            label=block.name,
        )
        participation = matching.participation_for_position(opt_match_id) if matching else None
        structure["signup_stats"] += SignupStats.ZERO.replace(
            min_count=0,
            max_count=None,  # allow_more -> always free
            missing=0,
            free=None,
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

    for _ in range(max(0, len(designated_for) - len(block.positions.all()) - allow_more_count)):
        # if more designated participants than we have positions, we need to add placeholder anyway
        opt_match_id = _build_position_id(block, next(opt_counter[str(block.id)]), path)
        p = Position(
            id=opt_match_id,
            required_qualifications=required_here,
            preferred_by=preferred_by,
            designated_for=designated_for,
            aux_score=0,
            required=False,  # designated -> always optional
            label=block.name,
        )
        participation = matching.participation_for_position(opt_match_id) if matching else None
        structure["signup_stats"] += SignupStats.ZERO.replace(
            min_count=0,
            max_count=0,  # designated overflow -> runs over max
            missing=0,
            free=0,
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


def _build_position_id(block, path, position_id):
    """
    For a given block, a counter providing running numbers and a path of blocks,
    construct an ID for the matching positions.
    """
    return f"{path}{block.uuid}-opt-{position_id}"


def convert_blocks_to_positions(starting_blocks, participations, matching=None):
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
    opt_counter = defaultdict(partial(itertools.count, 1))
    for block in starting_blocks:
        positions, sub_structure = _search_block(
            block,
            path=root_path,
            level=1,
            path_optional=False,
            required_qualifications=set(),
            participations=participations,
            opt_counter=opt_counter,
            matching=matching,
            parents=[],
        )
        all_positions.extend(positions)
        structure["sub_blocks"].append(sub_structure)
    structure["signup_stats"] = SignupStats.reduce(
        [s["signup_stats"] for s in structure["sub_blocks"]]
    )
    return all_positions, structure


def iter_atomic_blocks(structure):
    for sub_block in structure["sub_blocks"]:
        if not sub_block["is_composite"]:
            yield sub_block
        else:
            yield from iter_atomic_blocks(sub_block)
