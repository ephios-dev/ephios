from django import template

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
