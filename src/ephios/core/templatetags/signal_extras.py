import sys
from operator import itemgetter

from django import template
from django.utils.safestring import mark_safe

from ephios.core.signals import insert_html

register = template.Library()


@register.simple_tag(name="collect_insert_html_signal", takes_context=True)
def collect_insert_html(context, location, **kwargs):
    results = insert_html.send(
        sender=sys.intern(location + ""), request=context["request"], **kwargs
    )
    return mark_safe("\n".join(map(itemgetter(1), results)))
