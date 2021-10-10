import datetime

from django import template
from django.template.defaultfilters import floatformat

register = template.Library()


@register.filter(name="get")
def dict_get(dictionary, key):
    return dictionary.get(key)


@register.filter(name="sum")
def _sum(elements):
    return sum(elements)


@register.filter(name="getattr")
def _getattr(obj, key):
    return getattr(obj, str(key))


@register.filter(name="timedelta_in_hours")
def timedelta_in_hours(delta):
    return (
        floatformat(delta / datetime.timedelta(hours=1), 2)
        if isinstance(delta, datetime.timedelta)
        else delta
    )
