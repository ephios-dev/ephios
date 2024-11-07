import django_filters
from django.utils.translation import gettext_lazy as _
from django_filters import FilterSet, IsoDateTimeFilter, ModelMultipleChoiceFilter
from guardian.shortcuts import get_objects_for_user
from rest_framework.filters import BaseFilterBackend

from ephios.core.models import AbstractParticipation, Event, EventType, Shift


class ParticipationPermissionFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        events = get_objects_for_user(request.user, "core.view_event")
        return queryset.filter(shift__event__in=events)


class ShiftPermissionFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        events = get_objects_for_user(request.user, "core.view_event")
        return queryset.filter(event__in=events)


class StartEndTimeFilterSet(FilterSet):
    start_time = django_filters.rest_framework.IsoDateTimeFromToRangeFilter(label=_("start time"))
    end_time = django_filters.rest_framework.IsoDateTimeFromToRangeFilter(label=_("end time"))

    start_gte = IsoDateTimeFilter(
        field_name="start_time",
        lookup_expr="gte",
        label=_("start time greater than equals (deprecated, use start_time_after instead)"),
    )
    start_lte = IsoDateTimeFilter(
        field_name="start_time",
        lookup_expr="lte",
        label=_("start time less than equals (deprecated, use start_time_before instead)"),
    )


class ParticipationFilterSet(StartEndTimeFilterSet):
    event_type = ModelMultipleChoiceFilter(
        field_name="shift__event__type", label=_("event type"), queryset=EventType.objects.all()
    )
    event = ModelMultipleChoiceFilter(
        field_name="shift__event_id", label="event id", queryset=Event.objects.all()
    )
    shift = ModelMultipleChoiceFilter(
        field_name="shift_id", label="shift id", queryset=Shift.objects.all()
    )

    class Meta:
        model = AbstractParticipation
        fields = [
            "state",
        ]


class EventFilterSet(StartEndTimeFilterSet):

    class Meta:
        model = Event
        fields = [
            "type",
        ]
