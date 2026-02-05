import itertools
import logging
import uuid
from collections import defaultdict
from functools import cached_property, partial
from operator import attrgetter
from typing import Optional

from django import forms
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django_select2.forms import ModelSelect2Widget
from rest_framework import serializers

from ephios.core.models import AbstractParticipation
from ephios.core.services.matching import Matching, Position, match_participants_to_positions
from ephios.core.signup.disposition import BaseDispositionParticipationForm
from ephios.core.signup.flow.participant_validation import (
    ParticipantUnfitError,
    SignupDisallowedError,
)
from ephios.core.signup.forms import SignupForm
from ephios.core.signup.participants import AbstractParticipant
from ephios.core.signup.stats import SignupStats
from ephios.core.signup.structure.base import BaseShiftStructure
from ephios.plugins.baseshiftstructures.structure.common import MinimumAgeMixin
from ephios.plugins.baseshiftstructures.structure.group_common import (
    AbstractGroupBasedStructureConfigurationForm,
)
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
            and not position.designation_only
            for position in block["positions"]
        )
    ]


class ComplexDispositionParticipationForm(BaseDispositionParticipationForm):
    disposition_participation_template = "complexsignup/fragment_participation.html"
    unit_path = forms.ChoiceField(
        label=_("Unit"),
        required=False,
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        complex_structure = self.shift.structure
        complex_structure._assume_cache()

        qualified_blocks = atomic_block_participant_qualifies_for(
            complex_structure._structure, self.instance.participant
        )
        all_blocks = list(iter_atomic_blocks(complex_structure._structure))
        unqualified_blocks = [b for b in all_blocks if b not in qualified_blocks]

        self.fields["unit_path"].choices = [("", _("auto"))]
        if qualified_blocks:
            self.fields["unit_path"].choices += [
                (
                    _("qualified"),
                    [(b["path"], b["display_with_path"]) for b in qualified_blocks],
                )
            ]
        if unqualified_blocks:
            self.fields["unit_path"].choices += [
                (
                    _("unqualified"),
                    [(b["path"], b["display_with_path"]) for b in unqualified_blocks],
                )
            ]
        if preferred_unit_path := self.instance.structure_data.get("preferred_unit_path"):
            try:
                preferred_block = next(
                    filter(
                        lambda b: b["path"] == preferred_unit_path,
                        all_blocks,
                    )
                )
                self.preferred_unit_name = preferred_block["display_with_path"]
            except StopIteration:
                pass  # preferred block not found
        if initial := self.instance.structure_data.get("dispatched_unit_path"):
            self.fields["unit_path"].initial = initial

    def save(self, commit=True):
        self.instance.structure_data["dispatched_unit_path"] = self.cleaned_data["unit_path"]
        super().save(commit)


class StartingBlockForm(forms.Form):
    building_block = forms.ModelChoiceField(
        label=_("Unit"),
        widget=ModelSelect2Widget(
            model=BuildingBlock,
            search_fields=["name__icontains"],
            attrs={"data-minimum-input-length": 0},
        ),
        queryset=BuildingBlock.objects.all(),
    )
    label = forms.CharField(label=_("Label"), required=False)
    optional = forms.BooleanField(label=_("optional"), required=False)
    uuid = forms.CharField(widget=forms.HiddenInput, required=False)

    def clean_uuid(self):
        return self.cleaned_data.get("uuid") or uuid.uuid4()


StartingBlocksFormset = forms.formset_factory(
    StartingBlockForm, can_delete=True, min_num=1, validate_min=1, extra=0
)


class ComplexConfigurationForm(AbstractGroupBasedStructureConfigurationForm):
    template_name = "complexsignup/configuration_form.html"
    choose_preferred_team = None  # renamed
    choose_preferred_unit = forms.BooleanField(
        label=_("Participants must provide a preferred unit"),
        help_text=_("Participants will be asked during signup."),
        widget=forms.CheckboxInput,
        required=False,
        initial=False,
    )
    starting_blocks = forms.Field(
        label=_("Units"),
        widget=forms.HiddenInput,
        required=False,
    )
    formset_data_field_name = "starting_blocks"

    def get_formset_class(self):
        return StartingBlocksFormset

    @classmethod
    def format_formset_item(cls, item):
        try:
            return item["label"] or item["building_block"].name
        except AttributeError:
            # building block is an id
            try:
                return str(BuildingBlock.objects.get(id=item["building_block"]).name)
            except BuildingBlock.DoesNotExist:
                return gettext("Deleted unit")


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

    @cached_property
    def confirmed_participants(self):
        return [
            participation.participant
            for participation in self.shift.participations.all()
            if participation.state == AbstractParticipation.States.CONFIRMED
        ]

    @cached_property
    def participations(self):
        """
        Returns a list of all participations in the shift that are sorted by confirmed-then-requested.
        Other states are dropped.
        """
        return list(
            sorted(
                filter(
                    lambda p: (
                        p.state
                        in {
                            AbstractParticipation.States.REQUESTED,
                            AbstractParticipation.States.CONFIRMED,
                        }
                    ),
                    self.shift.participations.all(),
                ),
                key=attrgetter("state"),
                reverse=True,
            )
        )

    def _structure_match(self):
        participants = [participation.participant for participation in self.participations]
        all_positions, __ = build_structure_from_starting_blocks(
            self._starting_blocks, self.participations
        )
        self._matching = match_participants_to_positions(
            participants, all_positions, confirmed_participants=self.confirmed_participants
        )
        self._matching.attach_participations(self.participations)

        # let's work up the blocks again, but now with matching
        self._all_positions, self._structure = build_structure_from_starting_blocks(
            self._starting_blocks, self.participations, matching=self._matching
        )

        # for checking signup, we need a matching with only confirmed participations
        self._confirmed_only_matching = match_participants_to_positions(
            self.confirmed_participants,
            self._all_positions,
            confirmed_participants=self.confirmed_participants,
        )

        # we just have to add unpaired matches to the full stats
        self._signup_stats = self._structure["signup_stats"] + SignupStats.ZERO.replace(
            requested_count=sum(
                p.state == AbstractParticipation.States.REQUESTED
                for p in self._matching.unpaired_participations
            ),
            confirmed_count=sum(
                p.state == AbstractParticipation.States.CONFIRMED
                for p in self._matching.unpaired_participations
            ),
        )

    def _assume_cache(self):
        if not hasattr(self, "_cached_structure_match"):
            self._structure_match()
            self._cached_structure_match = True

    @cached_property
    def _starting_blocks(self):
        """
        Returns list of tuples of identifier, Building Block, label and optional.
        If there is no label, uses None. The identifier is a uuid kept per starting block
        and allows for later label/order change without losing disposition info.
        A block change is considered breaking and will trigger a change in identifier, because
        qualifications might not match afterwards.
        """
        qs = BuildingBlock.objects.all()
        id_to_block = {
            block.id: block
            for block in qs.filter(
                id__in=[unit["building_block"] for unit in self.configuration.starting_blocks]
            )
        }
        starting_blocks = []
        for unit in self.configuration.starting_blocks:
            if unit["building_block"] not in id_to_block:
                continue  # block missing from DB
            starting_blocks.append((
                unit["uuid"],
                id_to_block[unit["building_block"]],
                unit["label"],
                unit["optional"],
            ))
        return starting_blocks

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
            matching_with_this_participant = match_participants_to_positions(
                confirmed_participants + [participant], self._all_positions
            )
            if len(matching_with_this_participant.pairings) > len(
                self._confirmed_only_matching.pairings
            ):
                return
        if (free := self._signup_stats.free) and free > 0:
            raise ParticipantUnfitError(_("You are not qualified."))
        raise SignupDisallowedError(_("The maximum number of participants is reached."))

    def get_checkers(self):
        return super().get_checkers() + [
            partial(
                self.check_qualifications,
                strict_mode=not self.shift.signup_flow.uses_requested_state,
            )
        ]

    def get_list_export_data(self):
        self._assume_cache()
        export_data = []
        for block in iter_atomic_blocks(self._structure):
            for position, participation in zip(
                block["positions"],
                block["participations"],
            ):
                if not participation and not position.required:
                    continue
                export_data.append({
                    "participation": participation,
                    "required_qualifications": position.required_qualifications,
                    "description": block["display_with_path"],
                })
        return export_data

    def get_signup_form_fields(self, participant, participation, signup_choice):
        initial = participation.structure_data.get("preferred_unit_path")
        required = (
            signup_choice != SignupForm.SignupChoices.DECLINE
            and self.shift.structure.configuration.choose_preferred_unit
        )

        self._assume_cache()

        allowed_blocks = atomic_block_participant_qualifies_for(self._structure, participant)

        choices = [(b["path"], b["display_with_path"]) for b in allowed_blocks]

        help_text = ""
        unqualified_blocks = [
            b for b in iter_atomic_blocks(self._structure) if b not in allowed_blocks
        ]
        if unqualified_blocks:
            help_text = _("You don't qualify for {blocks}.").format(
                blocks=", ".join(set(b["display_with_path"] for b in unqualified_blocks))
            )

        return {
            "complexsignup_preferred_unit_path": {
                "label": _("Preferred Unit"),
                "help_text": help_text,
                "default": initial,
                "required": required,
                "form_class": forms.ChoiceField,
                "form_kwargs": {
                    "choices": choices,
                    "widget": forms.RadioSelect,
                },
                "serializer_class": serializers.ChoiceField,
                "serializer_kwargs": {
                    "choices": choices,
                },
            },
        }

    def save_signup(self, participant, participation, signup_choice, cleaned_data):
        if signup_choice != SignupForm.SignupChoices.DECLINE:
            participation.structure_data["preferred_unit_path"] = cleaned_data[
                "complexsignup_preferred_unit_path"
            ]
            participation.save(update_fields=["structure_data"])


def _build_display_name_long(block_name, composed_label, number):
    if composed_label and composed_label != block_name:
        return f"{composed_label} - {block_name} #{number}"
    return f"{block_name} #{number}"


def _build_display_path(parents, display_long):
    # put the display name first, in case the whole path gets cut off
    if parents := [s["display_short"] for s in reversed(parents)]:
        return f"{display_long} ({' » '.join(parents)})"
    return display_long


def iter_atomic_blocks(structure):
    for sub_block in structure["sub_blocks"]:
        if not sub_block["is_composite"]:
            yield sub_block
        else:
            yield from iter_atomic_blocks(sub_block)


def build_structure_from_starting_blocks(starting_blocks, participations, matching=None):
    """
    Create a tree structure from the given starting blocks, providing a plethora of information
    used for display, matching and signup validation.
    If a matching is provided, the signup stats will have correct participation counts,
    but only for matched participants.
    """
    root_path = "root."  # build a dot-seperated path used to identify blocks and positions.
    all_positions = []  # collect all positions in a list
    # The root block is "virtual", always composite and contains the starting blocks as sub_blocks.
    structure = {
        "is_composite": True,
        "positions": [],
        "position_match_ids": [],
        "sub_blocks": [],
        "path": root_path,
        "optional": False,
        "level": 0,
        "name": "ROOT",
        "qualification_label": "",
    }
    # The block usage counter is used to assign indices to usages of atomic blocks so they can be
    # differentiated in the matching algorithm as well as when displaying units.
    block_usage_counter = defaultdict(partial(itertools.count, 1))
    for identifier, block, label, optional in starting_blocks:
        positions, sub_structure = _search_block(
            block,
            path=f"{root_path}{identifier}.",
            level=1,
            path_optional=optional,
            required_qualifications=set(),
            participations=participations,
            block_usage_counter=block_usage_counter,
            matching=matching,
            parents=[],
            composed_label=label,
        )
        all_positions.extend(positions)
        structure["sub_blocks"].append(sub_structure)
    structure["signup_stats"] = SignupStats.reduce([
        s["signup_stats"] for s in structure["sub_blocks"]
    ])
    return all_positions, structure


def _search_block(
    block: BuildingBlock,
    path: str,
    level: int,
    required_qualifications: set,
    path_optional: bool,
    participations: list[AbstractParticipation],
    block_usage_counter,
    matching: Matching,
    parents: list,
    composed_label: Optional[str] = None,
):  # pylint: disable=too-many-locals
    """
    Recursively build a tree structure from the given block.
    Return all positions and a dict describing the structure at this block.
    """
    required_here = set(required_qualifications)
    for requirement in block.qualification_requirements.all():
        if not requirement.everyone:
            # "at least one" is not supported
            raise ValueError("unsupported requirement")
        required_here |= set(requirement.qualifications.all())

    all_positions = []
    number = next(block_usage_counter[block.name])
    display_long = _build_display_name_long(block.name, composed_label, number)
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
        "display_short": composed_label or block.name,
        "display_long": display_long,
        "display_with_path": _build_display_path(parents, display_long),
        "number": number,
        "qualification_label": ", ".join(q.abbreviation for q in required_here),
        "qualification_ids": {q.id for q in required_here},
        "parents": parents,
        "signup_stats": SignupStats.ZERO,
    }
    if block.is_composite():
        for composition in (
            block.sub_compositions
            .all()
            .select_related(
                "sub_block",
            )
            .prefetch_related(
                "sub_block__positions__qualifications",
                "sub_block__qualification_requirements__qualifications",
                "sub_block__sub_compositions",
            )
        ):
            positions, sub_structure = _search_block(
                block=composition.sub_block,
                path=f"{path}{composition.id}.",
                level=level + 1,
                required_qualifications=required_here,
                path_optional=path_optional or composition.optional,
                block_usage_counter=block_usage_counter,
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
            block_usage_counter,
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
    block_usage_counter,
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
    # for displaying count info about this block, keep a version of signup stats in which is
    # this block is never considered optional (path_optional)
    non_optional_signup_stats = SignupStats.ZERO
    for block_position in block.positions.all():
        match_id = _build_position_id(path, is_more=False, position_id=block_position.id)
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
        has_confirmed_participation = (
            participation is not None
            and participation.state == AbstractParticipation.States.CONFIRMED
        )
        structure["signup_stats"] += SignupStats(
            min_count=int(required),
            max_count=1,
            missing=int(required and not has_confirmed_participation),
            free=int(not has_confirmed_participation),
            requested_count=bool(
                participation and participation.state == AbstractParticipation.States.REQUESTED
            ),
            confirmed_count=has_confirmed_participation,
        )
        non_optional_signup_stats += SignupStats(
            min_count=int(not block_position.optional),
            max_count=1,
            missing=int(not block_position.optional and not has_confirmed_participation),
            free=int(not has_confirmed_participation),
            requested_count=bool(
                participation and participation.state == AbstractParticipation.States.REQUESTED
            ),
            confirmed_count=has_confirmed_participation,
        )
        all_positions.append(p)
        structure["positions"].append(p)
        structure["participations"].append(participation)

    # build derivative positions for "allow_more" participants
    allow_more_count = int(block.allow_more) * (
        len(participations) + 1
    )  # 1 extra in case of signup matching check
    for __ in range(allow_more_count):
        opt_match_id = _build_position_id(
            path, is_more=True, position_id=next(block_usage_counter[str(block.id)])
        )
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
        allow_more_stat = SignupStats(
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
        structure["signup_stats"] += allow_more_stat
        non_optional_signup_stats += allow_more_stat
        all_positions.append(p)
        structure["positions"].append(p)
        structure["participations"].append(participation)

    for __ in range(max(0, len(designated_for) - len(block.positions.all()) - allow_more_count)):
        # if more designated participants than we have positions, we need to add placeholder anyway
        opt_match_id = _build_position_id(
            path, is_more=True, position_id=next(block_usage_counter[str(block.id)])
        )
        p = Position(
            id=opt_match_id,
            required_qualifications=required_here,
            preferred_by=preferred_by,
            designated_for=designated_for,
            aux_score=0,
            required=False,  # designated -> always optional
            label=block.name,
            designation_only=True,
        )
        participation = matching.participation_for_position(opt_match_id) if matching else None
        overflow_stat = SignupStats(
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
        structure["signup_stats"] += overflow_stat
        non_optional_signup_stats += overflow_stat
        all_positions.append(p)
        structure["positions"].append(p)
        structure["participations"].append(participation)

    # used to check if this atomic block can be considered "free"
    structure["has_undesignated_positions"] = len(structure["positions"]) > len(designated_for)
    structure["non_optional_signup_stats"] = non_optional_signup_stats


def _build_position_id(path, is_more, position_id):
    """
    Return a string identifying a position, give by a path identifying the atomic block,
     some modestring differentiating the origin of the position id, and an id for the position.
    """
    # For use of Position.pk, use "pk" as modestring, for other positions "more". This way,
    # there are no collisions of count and pk.
    modestring = "more" if is_more else "pk"
    return f"{path}{modestring}-{position_id}"
