import dataclasses
import itertools
import logging

from django import template

from ephios.core.services.matching import match_participants_to_positions
from ephios.core.signup.participants import PlaceholderParticipant
from ephios.core.signup.stats import SignupStats
from ephios.plugins.baseshiftstructures.structure.group_common import format_min_max_count

logger = logging.getLogger(__name__)
register = template.Library()


@register.filter(name="find_complex_participation")
def find_complex_participation(matching, position_id: str):
    return matching.participation_for_position(position_id)


@register.filter(name="format_min_max_count")
def format_min_max_count_filter(signup_stats: SignupStats):
    return format_min_max_count(
        min_count=signup_stats.min_count,
        max_count=signup_stats.max_count,
    )


@register.filter(name="has_complex_free")
def has_complex_free(atomic_block_structure, shift):
    """
    This does a "has_free" check similar to the one in qualification mix.
    It answers the question:
    Could another participant sign up for this basic unit?
    """
    # We can't just return False if the signup stats say it has no free,
    # because we might be able to make space by moving around participants.
    if atomic_block_structure["signup_stats"].has_free():
        # If it is free in the current matching, we can return True.
        return True
    if not atomic_block_structure["has_undesignated_positions"]:
        # Moving the participants away is only possible
        # if there is some none designated position for this block.
        return False

    structure = shift.structure
    # pylint: disable=protected-access
    structure._assume_cache()

    if not structure._signup_stats.has_free():
        # There's nothing free to move participants to anyway.
        return False

    # At this point, we might be able to move occupants away. We can try matching
    # by designating a qualified placeholder participant for this block and seeing
    # if the matching produces one less unmatched position. That would mean that
    # participants previously occupying this block can also cover another position.
    # We use an extra participant that qualifies for every position in this block.
    # An alternative would be to try for each position individually, and try to match
    # the extra participant anywhere (making them exchangeable with someone occupying
    # this block), but this requires multiple matches, which is slow.
    # This is also why we cannot use the plain structures qualification checker,
    # which does something similar, but is not specific to a block.

    # Collect every qualification required for every position in this block.
    qualifications = frozenset(
        itertools.chain(*[
            pos.required_qualifications for pos in atomic_block_structure["positions"]
        ])
    )
    extra_participant = PlaceholderParticipant(
        "Extra participant",
        qualifications,
        None,
        None,
    )
    # Add a designation to force the extra participant into this block.
    modified_positions = [
        (
            dataclasses.replace(
                position, designated_for=position.designated_for | {extra_participant}
            )
            if position.id.startswith(atomic_block_structure["path"])
            else position
        )
        for position in structure._all_positions
    ]
    # Return if a matching produces less unpaired positions.
    matching_with_extra = match_participants_to_positions(
        structure.confirmed_participants + [extra_participant], modified_positions
    )
    return len(matching_with_extra.unpaired_positions) < len(
        shift.structure._confirmed_only_matching.unpaired_positions
    )
