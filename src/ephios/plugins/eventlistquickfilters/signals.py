from django.dispatch import receiver
from django.template.loader import render_to_string

from ephios.core.signals import (
    HTML_EVENT_LIST_HEADER,
    event_list_filter_initial,
    insert_html,
)
from ephios.plugins.eventlistquickfilters.models import EventListQuickFilter


def _get_visible_filters(request):
    return (
        EventListQuickFilter.objects
        .filter(visible_for_groups__in=request.user.groups.all())
        .prefetch_related("filter_types")
        .distinct()
        .order_by("position")
    )


@receiver(
    event_list_filter_initial,
    dispatch_uid="ephios.plugins.eventlistquickfilters.signals.filter_form_inital",
)
def filter_form_initial(sender, request, **kwargs):
    default_filter = (
        _get_visible_filters(request)
        .filter(default_for_groups__in=request.user.groups.all())
        .first()
    )
    if default_filter is None:
        return {}
    return {
        "types": list(default_filter.filter_types.all().values_list("id", flat=True)),
    }


@receiver(
    insert_html,
    sender=HTML_EVENT_LIST_HEADER,
    dispatch_uid="ephios.plugins.eventlistquickfilters.signals.event_list_html",
)
def event_list_html(sender, request, **kwargs):
    visible_filters = _get_visible_filters(request)
    if not visible_filters:
        return ""

    default_filter = visible_filters.filter(
        default_for_groups__in=request.user.groups.all()
    ).first()

    for filter in visible_filters:
        filter.mark_is_active(request, used_as_default=filter == default_filter)

    return render_to_string(
        "eventlistquickfilters/filter_buttons.html",
        {
            "filters": visible_filters,
        },
        request=request,
    )
