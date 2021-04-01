import itertools

from django import template
from django.db import models

from ephios.modellogging.log import LOGGED_MODELS

register = template.Library()


@register.filter(name="related_logentries")
def related_logentries(instance):
    return LOGGED_MODELS[type(instance)].related_logentries(instance)


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
