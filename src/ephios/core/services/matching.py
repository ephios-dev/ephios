import dataclasses
import itertools
from typing import Collection, Optional

from django.utils.functional import cached_property
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import min_weight_full_bipartite_matching

from ephios.core.models import Qualification
from ephios.core.services.qualification import QualificationUniverse
from ephios.core.signup.participants import AbstractParticipant

# pylint: disable=too-many-instance-attributes too-many-locals


@dataclasses.dataclass(unsafe_hash=True)
class Position:
    id: str
    required: bool
    required_qualifications: Collection[Qualification]
    designated_for: Collection[AbstractParticipant]  # designated by disposition
    preferred_by: Collection[AbstractParticipant]  # preferred by participant (less important)
    label: Optional[str] = None
    aux_score: float = 0.0  # additional score control in range [0,1]
    designation_only: bool = (
        False  # if this Position was created purely out of overdesignation, mark it here
    )

    def __post_init__(self):
        self.required_qualifications = frozenset(self.required_qualifications)
        self.preferred_by = frozenset(self.preferred_by)
        self.designated_for = frozenset(self.designated_for)

    @cached_property
    def required_skill(self):
        graph = QualificationUniverse.get_graph()
        required_qualification_uuids = [
            qualification.uuid for qualification in self.required_qualifications
        ]
        return set(graph.spread_from(required_qualification_uuids))

    @cached_property
    def skill_level(self):
        return skill_level(self.required_skill)


def skill_level(qualifications):
    """
    skill_level is some float in the range [0,1] that expresses
    how far up in the qualification hierarchy the required qualifications are.
    """
    if not qualifications:
        return 0
    qualifications = list(qualifications)
    # convert to uuids
    if isinstance(qualifications[0], Qualification):
        qualifications = [q.uuid for q in qualifications]
    graph = QualificationUniverse.get_graph()
    required_skill = frozenset(graph.spread_from(qualifications))
    # all_skill is qualifications up and down from the required ones
    all_skill = required_skill | frozenset(graph.spread_reverse(qualifications))
    return len(required_skill) / len(all_skill)


class Matching:
    def __init__(self, participants, positions, pairings):
        self.pairings = pairings
        self.participants = participants
        self.positions = positions
        self.unpaired_participants = set(participants)
        self.unpaired_positions = list(
            sorted(positions, key=lambda position: (-position.skill_level, position.id))
        )
        for participant, position in pairings:
            self.unpaired_participants.remove(participant)
            self.unpaired_positions.remove(position)
        self._participations = None

    @property
    def participations(self):
        if self._participations is None:
            raise ValueError("participations not attached")
        return self._participations

    def attach_participations(self, participations):
        self._participations = participations

    @cached_property
    def _participation_by_participant(self):
        return {p.participant: p for p in self.participations}

    @cached_property
    def participation_pairings(self):
        return [
            (self._participation_by_participant[participant], position)
            for participant, position in self.pairings
        ]

    @cached_property
    def unpaired_participations(self):
        return [
            participation
            for participation in self.participations
            if participation.participant in self.unpaired_participants
        ]

    def participation_for_position(self, position_id):
        for participation, position in self.participation_pairings:
            if position.id == position_id:
                return participation


# negative scores get rejected as pairings, so these values must be chosen in a way that valid pairings never go < 0
# (e.g. valid designation but skill issue --> MAX_SKILL_VALUE way smaller than designated_unqualified_value)
BASE_SCORE = 5.0
PREFERRED_VALUE = 3.0
MAX_AUX_VALUE = 2.0
CONFIRMED_VALUE = 2.0
MAX_SKILL_VALUE = 1.0
CONSTANT_SUM = BASE_SCORE + PREFERRED_VALUE + MAX_SKILL_VALUE + CONFIRMED_VALUE + MAX_AUX_VALUE


def score_pairing(
    participant: AbstractParticipant,
    position: Position,
    participant_is_confirmed,
    participant_has_designation,
    number_of_participants=1_000_000,
):
    """
    Score the pairing of participant and  position.
    Skill here means a set of qualification.
    """
    # number of participants is used as a scoring value to make sure that in adverse cases
    # a matching with some unqualified pairings gets a worse score than a matching with more valid pairings
    # (similar for prefers and skill level). It can be arbitrarily big, but must be at least bigger than the sum of
    # all the other constants used in the score.
    padded_participant_count = 10 + 2 * number_of_participants
    required_value = padded_participant_count * CONSTANT_SUM
    designated_unqualified_value = required_value * required_value
    designated_and_qualified_value = 2 * designated_unqualified_value
    undesignated_unqualified_value = designated_unqualified_value * designated_unqualified_value

    is_designated = participant in position.designated_for
    is_qualified = position.required_skill <= participant.skill

    if not is_designated and (
        not is_qualified or position.designation_only or participant_has_designation
    ):
        # the participant does not have some required skill or is designated elsewhere
        return -undesignated_unqualified_value  # avoid matching unqualified participants

    score = BASE_SCORE
    if is_designated:
        if is_qualified:
            score += designated_and_qualified_value
        else:
            # designated participants get assigned even if they don't qualify, and at a lower score
            score += designated_unqualified_value

    if participant in position.preferred_by:
        score += PREFERRED_VALUE
    if position.required:
        score += required_value
    if participant_is_confirmed:
        score += CONFIRMED_VALUE

    if is_qualified:
        # if qualified, lets prefer high skill positions
        score += position.skill_level * MAX_SKILL_VALUE
    else:
        # if not qualified (but designated), let's prefer low skill positions
        score -= position.skill_level * MAX_SKILL_VALUE

    score += position.aux_score * MAX_AUX_VALUE
    return score


def match_participants_to_positions(
    participants: Collection[AbstractParticipant],
    positions: Collection[Position],
    confirmed_participants: Collection[AbstractParticipant] = None,
) -> Matching:
    participants = list(participants)
    positions = list(positions)
    confirmed_participants = (
        frozenset(confirmed_participants) if confirmed_participants else frozenset()
    )
    designated_participants = frozenset(
        itertools.chain(*(position.designated_for for position in positions))
    )
    costs = csr_matrix([
        [
            -score_pairing(
                participant,
                position,
                number_of_participants=len(participants),
                participant_is_confirmed=is_confirmed,
                participant_has_designation=has_designation,
            )
            for position in positions
        ]
        for participant, is_confirmed, has_designation in zip(
            participants,
            map(lambda p: p in confirmed_participants, participants),
            map(lambda p: p in designated_participants, participants),
        )
    ])
    matching = min_weight_full_bipartite_matching(costs)
    pairings = set()
    for par_idx, pos_idx in zip(*matching):
        cost = costs[par_idx, pos_idx]
        if cost <= 0:
            pairings.add((participants[par_idx], positions[pos_idx]))
    return Matching(participants, positions, pairings)
