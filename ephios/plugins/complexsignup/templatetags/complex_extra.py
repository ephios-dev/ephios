import itertools
import logging

from django import template

from ephios.core.signup.flow.participant_validation import SignupDisallowedError
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
    This does a "has_free" check similar to the one in qualification mix. It answers the question:
    Could another participant sign up for this atomic block?
    """

    # assume the participant has every qualification needed in this block
    qualifications = set(
        itertools.chain(
            *[pos.required_qualifications for pos in atomic_block_structure["positions"]]
        )
    )
    try:
        extra_participant = PlaceholderParticipant(
            "Extra participant",
            qualifications,
            None,
            None,
        )
        shift.structure.check_qualifications(shift, extra_participant, strict_mode=True)
        return True
    except SignupDisallowedError:
        return False
