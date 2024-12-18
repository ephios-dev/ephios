# inspired by https://jfelix.info/blog/how-to-make-a-text-color-fit-any-background-color
from math import sqrt

from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key

from ephios.core.models import EventType


def calculate_luminance(rgb: tuple):
    r, g, b = map(
        lambda channel: (
            channel / 255 / 12.92
            if channel / 255 <= 0.03928
            else ((channel / 255 + 0.055) / 1.055) ** 2.4
        ),
        rgb,
    )
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def get_text_color_for_background(background_luminance: int):
    return "#000000" if background_luminance > sqrt(1.05 * 0.05) - 0.05 else "#ffffff"


def get_eventtype_color_style(eventtype: EventType):
    luminance = calculate_luminance(
        (
            int(eventtype.color[1:3], 16),
            int(eventtype.color[3:5], 16),
            int(eventtype.color[5:7], 16),
        )
    )
    text_color = get_text_color_for_background(luminance)
    return (
        f".eventtype-{eventtype.pk}-color{{background-color:{eventtype.color};color:{text_color};}}"
    )


def clear_eventtype_color_css_fragment_cache():
    key = make_template_fragment_key("eventtype_colors_css", vary_on=None)
    cache.delete(key)
