from django import template

from ephios.core.signup.stats import SignupStats
from ephios.plugins.baseshiftstructures.structure.group_common import format_min_max_count

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
