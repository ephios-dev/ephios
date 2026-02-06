import django_filters
from django.db.models import Max, Min, Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from oauth2_provider.contrib.rest_framework import IsAuthenticatedOrTokenHasScope
from rest_framework import filters, viewsets
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework_guardian import filters as guardian_filters

from ephios.api.filters import (
    EventFilterSet,
    ParticipationFilterSet,
    ParticipationPermissionFilter,
    ShiftPermissionFilter,
    StartEndTimeFilterSet,
    UserinfoParticipationPermissionFilter,
)
from ephios.api.permissions import ViewUserModelObjectPermissions
from ephios.api.serializers import (
    EventSerializer,
    ParticipationSerializer,
    ShiftSerializer,
    UserinfoParticipationSerializer,
)
from ephios.core.models import AbstractParticipation, Event, Shift


class ShiftViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ShiftSerializer
    permission_classes = [DjangoObjectPermissions, IsAuthenticatedOrTokenHasScope]
    filter_backends = [
        django_filters.rest_framework.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
        ShiftPermissionFilter,
    ]
    filterset_class = StartEndTimeFilterSet
    required_scopes = ["PUBLIC_READ"]
    queryset = Shift.objects.all()


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EventSerializer
    filterset_class = EventFilterSet
    search_fields = ["title", "description", "location"]
    ordering_fields = ["start_time", "end_time", "title"]
    ordering = ("start_time", "end_time")
    permission_classes = [DjangoObjectPermissions, IsAuthenticatedOrTokenHasScope]
    required_scopes = ["PUBLIC_READ"]

    filter_backends = [
        django_filters.rest_framework.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
        guardian_filters.ObjectPermissionsFilter,
    ]

    queryset = (
        Event.objects
        .all()
        .annotate(
            start_time=Min("shifts__start_time"),
            end_time=Max("shifts__end_time"),
        )
        .select_related("type")
        .prefetch_related("shifts")
        .prefetch_related(Prefetch("shifts__participations"))
        .order_by("start_time")
    )


class UserinfoParticipationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserinfoParticipationSerializer
    permission_classes = [ViewUserModelObjectPermissions, IsAuthenticatedOrTokenHasScope]
    filter_backends = [UserinfoParticipationPermissionFilter, DjangoFilterBackend]
    filterset_class = ParticipationFilterSet
    required_scopes = ["CONFIDENTIAL_READ"]

    queryset = (
        AbstractParticipation.objects
        .all()
        .select_related("shift", "shift__event", "shift__event__type")
        .order_by("id")
    )


class ParticipationViewSet(UserinfoParticipationViewSet):
    """
    Remove information that would not be visible in the web version,
    i.e. no email and date of birth of participants
    """

    serializer_class = ParticipationSerializer
    filter_backends = [ParticipationPermissionFilter, DjangoFilterBackend]
    permission_classes = [IsAuthenticatedOrTokenHasScope]
    required_scopes = ["CONFIDENTIAL_READ"]

    queryset = (
        AbstractParticipation.objects
        .filter(state__in=AbstractParticipation.States.REQUESTED_AND_CONFIRMED)
        .select_related("shift", "shift__event", "shift__event__type")
        .order_by("id")
    )
