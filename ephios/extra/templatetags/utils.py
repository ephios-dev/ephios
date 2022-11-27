import datetime

from django import template
from django.template.defaultfilters import floatformat
from django.urls import reverse
from django.utils.safestring import mark_safe

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


@register.filter(name="workinghour_origin_link")
def workinghour_origin_link(workinghour):
    if workinghour["type"] == "event":
        url = reverse("core:event_detail", kwargs={"pk": workinghour["origin_id"], "slug": "none"})
        return mark_safe(f'<a href="{url}">View event</a>')
    elif workinghour["type"] == "request":
        edit_url = reverse("core:workinghour_edit", kwargs={"pk": workinghour["origin_id"]})
        delete_url = reverse("core:workinghour_delete", kwargs={"pk": workinghour["origin_id"]})
        return mark_safe(f'<a href="{edit_url}">Edit</a> <a href="{delete_url}">Delete</a>')
