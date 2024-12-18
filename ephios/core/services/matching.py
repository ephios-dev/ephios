import dataclasses
from typing import Collection, Optional

from django.utils.functional import cached_property
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import min_weight_full_bipartite_matching

from ephios.core.models import Qualification
from ephios.core.services.qualification import QualificationUniverse
from ephios.core.signup.participants import AbstractParticipant


@dataclasses.dataclass(unsafe_hash=True)
class Position:
    id: str
    required: bool
    required_qualifications: Collection[Qualification]
    designated_for: Collection[AbstractParticipant]  # designated by disposition
    preferred_by: Collection[AbstractParticipant]  # preferred by participant (less important)
    label: Optional[str] = None
    aux_score: float = 0.0  # additional score control in range [0,1]

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
    required_skill = set(graph.spread_from(qualifications))
    # all_skill is qualifications up and down from the required ones
    all_skill = required_skill | set(graph.spread_reverse(qualifications))
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


def score_pairing(
    participant: AbstractParticipant,
    position: Position,
    confirmed_participants,
    number_of_participants=1_000_000,
):
    """
    Score the pairing of participant and  position.
    Skill here means a set of qualification.
    """
    # number of participants is used as a scoring value to make sure that in adverse cases
    # a matching with a someone unqualified pairings gets a worse score than a matching with more valid pairings
    # (similar for prefers and skill level). It can be arbitrarily big, but must be at least bigger than the sum of
    # all the other constants used in the score.
    padded_participant_count = 10 + 2 * number_of_participants
    base_score = 1.0
    preferred_value = 3.0
    max_aux_value = 2.0
    confirmed_value = 2.0
    max_skill_value = 1.0
    required_value = padded_participant_count * sum(
        (base_score, preferred_value, max_skill_value, confirmed_value, max_aux_value)
    )
    designated_value = required_value**2
    unqualified_penalty = designated_value**2

    is_designated = participant in position.designated_for
    # optimally, we should reject a pairing for a participant designated for another position,
    # but we don't have that info here.

    if not is_designated and not position.required_skill <= participant.skill:
        # the participant does not have some required skill
        return -unqualified_penalty  # avoid matching unqualified participants

    score = base_score
    if is_designated:
        score += designated_value
    if participant in position.preferred_by:
        score += preferred_value
    if position.required:
        score += required_value
    if participant in confirmed_participants:
        score += confirmed_value
    score += position.skill_level * max_skill_value
    score += position.aux_score * max_aux_value
    return score


def match_participants_to_positions(
    participants: Collection[AbstractParticipant],
    positions: Collection[Position],
    confirmed_participants: Collection[AbstractParticipant] = None,
) -> Matching:
    participants = list(participants)
    positions = list(positions)
    confirmed_participants = list(confirmed_participants) if confirmed_participants else []
    costs = csr_matrix(
        [
            [
                -score_pairing(
                    participant,
                    position,
                    number_of_participants=len(participants),
                    confirmed_participants=confirmed_participants,
                )
                for position in positions
            ]
            for participant in participants
        ]
    )
    matching = min_weight_full_bipartite_matching(costs)
    pairings = set()
    for par_idx, pos_idx in zip(*matching):
        cost = costs[par_idx, pos_idx]
        if cost <= 0:
            pairings.add((participants[par_idx], positions[pos_idx]))
    return Matching(participants, positions, pairings)
