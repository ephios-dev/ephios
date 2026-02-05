import django_filters
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django_filters import FilterSet, IsoDateTimeFilter, ModelMultipleChoiceFilter
from guardian.shortcuts import get_objects_for_user
from rest_framework.filters import BaseFilterBackend

from ephios.core.models import AbstractParticipation, Event, EventType, Shift


class ParticipationPermissionFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        # to view public participation information (excl. email) you need to
        # * be able to see the event AND
        # * the event types' show_participation_data mode must fit
        return queryset.viewable_by(request.user.as_participant())


class UserinfoParticipationPermissionFilter(ParticipationPermissionFilter):
    def filter_queryset(self, request, queryset, view):
        # to also see user info of participations (incl. email) you need to
        # * see the event AND
        # * ANY of
        #   * has view_userprofile permission
        #   * can view user object
        #   * refers to request.user
        qs = super().filter_queryset(request, queryset, view)
        if not request.user.has_perm("core.view_userprofile"):
            viewable_users = get_objects_for_user(request.user, "core.view_userprofile")
            qs = qs.filter(
                Q(LocalParticipation___user=request.user)
                | Q(LocalParticipation___user__in=viewable_users)
            )
        return qs


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
