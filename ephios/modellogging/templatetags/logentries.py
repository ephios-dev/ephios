import itertools

from django import template
from django.db import models
from django.utils.safestring import mark_safe

from ephios.modellogging.log import LOGGED_MODELS
from ephios.modellogging.models import LogEntry

register = template.Library()


@register.filter(name="linkify_absolute_url")
def linkify_absolute_url(instance):
    if hasattr(instance, "get_absolute_url"):
        return mark_safe(
            f'<a class="log-absolute-url" href="{instance.get_absolute_url()}">{str(instance)}</a>'
        )
    return instance


@register.filter(name="related_logentries")
def related_logentries(instance):
    return LOGGED_MODELS[type(instance)].related_logentries(instance)


@register.filter(name="visible_logentries")
def visible_logentries(user):
    if user.has_perm("modellogging.view_logentry"):
        return LogEntry.objects.all()[:5]
    else:
        return LogEntry.objects.none()


@register.filter(name="group_logentries")
def group_logentries(logentries):
    if isinstance(logentries, models.QuerySet):
        logentries.select_related("user")
    yield from (
        list(group)
        for key, group in itertools.groupby(
            logentries,
            lambda entry: entry.request_id or entry.pk,
        )
    )
