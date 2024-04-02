from django_filters import DateTimeFilter, ModelChoiceFilter
from django_filters.rest_framework import FilterSet
from guardian.shortcuts import get_objects_for_user
from rest_framework.filters import BaseFilterBackend

from ephios.core.models import EventType, LocalParticipation


class ParticipationPermissionFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        events = get_objects_for_user(request.user, "core.view_event")
        return queryset.filter(shift__event__in=events)


class ParticipationFilterSet(FilterSet):
    # we cannot use gettext_lazy as it breaks sphinxcontrib.openapi (https://github.com/sphinx-contrib/openapi/issues/153)
    event_type = ModelChoiceFilter(
        field_name="shift__event__type", label="event type", queryset=EventType.objects.all()
    )
    from_date = DateTimeFilter(field_name="shift__start_time", lookup_expr="gte", label="from")
    to_date = DateTimeFilter(field_name="shift__end_time", lookup_expr="lte", label="to")

    class Meta:
        model = LocalParticipation
        fields = ["state"]
