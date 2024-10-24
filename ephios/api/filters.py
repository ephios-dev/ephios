from django_filters import FilterSet, IsoDateTimeFilter, ModelChoiceFilter
from django_filters.rest_framework import FilterSet
from guardian.shortcuts import get_objects_for_user
from rest_framework.filters import BaseFilterBackend

from ephios.core.models import Event, EventType, LocalParticipation


class ParticipationPermissionFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        events = get_objects_for_user(request.user, "core.view_event")
        return queryset.filter(shift__event__in=events)


class StartEndTimeFilterSet(FilterSet):
    start_time = IsoDateTimeFilter(field_name="start_time", label="start time")
    start_time__gt = IsoDateTimeFilter(
        field_name="start_time", lookup_expr="gt", label="start time greater than"
    )
    start_time__gte = IsoDateTimeFilter(
        field_name="start_time", lookup_expr="gte", label="start time greater than equals"
    )
    start_time__lt = IsoDateTimeFilter(
        field_name="start_time", lookup_expr="lt", label="start time less than"
    )
    start_time__lte = IsoDateTimeFilter(
        field_name="start_time", lookup_expr="lte", label="start time less than equals"
    )

    start_gte = IsoDateTimeFilter(
        field_name="start_time", lookup_expr="gte", label="start time greater than equals"
    )  # deprecated
    start_lte = IsoDateTimeFilter(
        field_name="start_time", lookup_expr="lte", label="start time less than equals"
    )  # deprecated

    end_time = IsoDateTimeFilter(field_name="end_time", label="end time")
    end_time__gt = IsoDateTimeFilter(
        field_name="end_time", lookup_expr="gt", label="end time greater than"
    )
    end_time__gte = IsoDateTimeFilter(
        field_name="end_time", lookup_expr="gte", label="end time greater than equals"
    )
    end_time__lt = IsoDateTimeFilter(
        field_name="end_time", lookup_expr="lt", label="end time less than"
    )
    end_time__lte = IsoDateTimeFilter(
        field_name="end_time", lookup_expr="lte", label="end time less than equals"
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
