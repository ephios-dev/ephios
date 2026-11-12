from django.dispatch import receiver
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from ephios.core.models import EventType
from ephios.core.signals import (
    HTML_EVENT_LIST_TOGGLES,
    event_list_filter_initial,
    insert_html,
    settings_sections,
)
from ephios.core.views.settings import SETTINGS_MANAGEMENT_SECTION_KEY
from ephios.plugins.eventlistquickfilters.models import EventListQuickFilter


def _get_visible_filters(request):
    return (
        EventListQuickFilter.objects
        .filter(visible_for_groups__in=request.user.groups.all())
        .prefetch_related("filter_types")
        .distinct()
        .order_by("position", "id")
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


def get_filter_template_data(request):
    visible_filters = _get_visible_filters(request)
    if not visible_filters:
        return []

    filter_data = []

    default_filter = visible_filters.filter(
        default_for_groups__in=request.user.groups.all()
    ).first()
    all_ids = EventType.objects.all().values_list("id", flat=True)
    GET_types = set(request.GET.getlist("types"))

    for filter in visible_filters:
        filter_types = set(map(str, filter.get_types_ids()))
        # if no types are given, a potential default filter is active
        used_as_default = filter.id == default_filter.id if default_filter else False
        if not GET_types and used_as_default:
            is_active = True
        else:
            is_active = GET_types == filter_types
        filter_data.append({
            "label": filter.label,
            "is_active": is_active,
            "used_as_default": used_as_default,
            "activate_types": filter.get_types_ids() if not used_as_default else None,
            "deactivate_types": all_ids if filter.show_all_types_on_deactivation else None,
        })
    return filter_data


@receiver(
    insert_html,
    sender=HTML_EVENT_LIST_TOGGLES,
    dispatch_uid="ephios.plugins.eventlistquickfilters.signals.event_list_html",
)
def event_list_html(sender, request, **kwargs):

    return render_to_string(
        "eventlistquickfilters/filter_buttons.html",
        {
            "filters": get_filter_template_data(request),
        },
        request=request,
    )


@receiver(
    settings_sections,
    dispatch_uid="ephios.plugins.eventlistquickfilters.signals.eventlistquickfilters_settings_section",
)
def settings_section(sender, request, **kwargs):
    return (
        [
            {
                "label": _("Event List Quick Filters"),
                "url": reverse("eventlistquickfilters:eventlistquickfilter_list"),
                "active": request.resolver_match.url_name.startswith("eventlistquickfilter"),
                "group": SETTINGS_MANAGEMENT_SECTION_KEY,
            },
        ]
        if request.user.has_perm("core.add_eventtype")
        else []
    )
