import itertools

from django import template

register = template.Library()


@register.filter(name="group_logentries")
def group_logentries(queryset):
    yield from (
        list(group)
        for key, group in itertools.groupby(
            queryset.select_related("user"),
            lambda entry: entry.request_id or entry.pk,
        )
    )
