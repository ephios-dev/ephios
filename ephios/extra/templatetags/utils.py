import datetime

from django import template
from django.template.defaultfilters import floatformat

register = template.Library()


@register.simple_tag
def setvar(value=None):
    """
    as an alternative to using with blocks and template, use
    `{% setvar value|filter:param as var %}` to save a value to a variable in a template.
    The builtin `firstof` doesn't work, because it converts values to strings.
    From here: https://pythoncircle.com/post/701/how-to-set-a-variable-in-django-template/
    """
    return value


@register.filter(name="get")
def dict_get(dictionary, key):
    return dictionary.get(key)


@register.filter
def get_items_for_key(dictionary, key):
    return dictionary.get(key).items()


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
