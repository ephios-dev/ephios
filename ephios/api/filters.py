import django_filters
from django_filters import FilterSet, IsoDateTimeFilter, ModelChoiceFilter
from guardian.shortcuts import get_objects_for_user
from rest_framework.filters import BaseFilterBackend

from ephios.core.models import Event, EventType, LocalParticipation


class ParticipationPermissionFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        events = get_objects_for_user(request.user, "core.view_event")
        return queryset.filter(shift__event__in=events)


class ShiftPermissionFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        events = get_objects_for_user(request.user, "core.view_event")
        return queryset.filter(event__in=events)


class StartEndTimeFilterSet(FilterSet):
    start_time = django_filters.rest_framework.IsoDateTimeFromToRangeFilter(label="start time")
    end_time = django_filters.rest_framework.IsoDateTimeFromToRangeFilter(label="end time")

    start_gte = IsoDateTimeFilter(
        field_name="start_time",
        lookup_expr="gte",
        label="start time greater than equals (deprecated, use start_time_after instead)",
    )
    start_lte = IsoDateTimeFilter(
        field_name="start_time",
        lookup_expr="lte",
        label="start time less than equals (deprecated, use start_time_before instead)",
    )


class ParticipationFilterSet(StartEndTimeFilterSet):
    # we cannot use gettext_lazy as it breaks sphinxcontrib.openapi (https://github.com/sphinx-contrib/openapi/issues/153)
    event_type = ModelChoiceFilter(
        field_name="shift__event__type", label="event type", queryset=EventType.objects.all()
    )

    class Meta:
        model = LocalParticipation
        fields = ["state"]


class EventFilterSet(StartEndTimeFilterSet):

    class Meta:
        model = Event
        fields = [
            "type",
        ]
