import django_filters
from django.db.models import Max, Min, Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from oauth2_provider.contrib.rest_framework import IsAuthenticatedOrTokenHasScope
from rest_framework import filters, viewsets
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework_guardian import filters as guardian_filters

from ephios.api.filters import (
    AbstractParticipationFilterSet,
    EventFilterSet,
    ParticipationPermissionFilter,
    ShiftPermissionFilter,
    StartEndTimeFilterSet,
)
from ephios.api.permissions import ParticipationPermissions
from ephios.api.serializers import AbstractParticipationSerializer, EventSerializer, ShiftSerializer
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
        Event.objects.all()
        .annotate(
            start_time=Min("shifts__start_time"),
            end_time=Max("shifts__end_time"),
        )
        .select_related("type")
        .prefetch_related("shifts")
        .prefetch_related(Prefetch("shifts__participations"))
        .order_by("start_time")
    )


class ParticipationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AbstractParticipationSerializer
    permission_classes = [ParticipationPermissions, IsAuthenticatedOrTokenHasScope]
    filter_backends = [ParticipationPermissionFilter, DjangoFilterBackend]
    filterset_class = AbstractParticipationFilterSet
    required_scopes = ["CONFIDENTIAL_READ"]

    queryset = (
        AbstractParticipation.objects.all()
        .select_related("shift", "shift__event", "shift__event__type")
        .order_by("id")
    )
