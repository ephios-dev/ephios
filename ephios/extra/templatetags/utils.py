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


@register.simple_tag(takes_context=True)
def param_replace(context, **kwargs):
    """
    Replace parameters in the GET query and urlencode them back.
    Usage in <a> tag:
    href="?{% param_replace overwrite_key=1 delete_this_key=None %}"
    """
    params = context["request"].GET.copy()
    for key, value in kwargs.items():
        if value is None and key in params:
            del params[key]
        elif value is not None:
            params[key] = str(value)
    return params.urlencode(safe="[]")


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
