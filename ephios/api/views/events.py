import django_filters
from django.db.models import Max, Min, Prefetch
from oauth2_provider.contrib.rest_framework import IsAuthenticatedOrTokenHasScope
from rest_framework import filters, serializers, viewsets
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework_guardian import filters as guardian_filters

from ephios.api.fields import ChoiceDisplayField
from ephios.api.filters import EventFilterSet, ShiftPermissionFilter, StartEndTimeFilterSet
from ephios.core.models import AbstractParticipation, Event, EventType, LocalParticipation, Shift
from ephios.core.templatetags.settings_extras import make_absolute


class SignupStatsSerializer(serializers.Serializer):
    # Stats are read only, so we don't implement create and update:
    # pylint: disable=abstract-method
    requested_count = serializers.IntegerField()
    confirmed_count = serializers.IntegerField()
    missing = serializers.IntegerField()
    free = serializers.IntegerField()
    min_count = serializers.IntegerField()
    max_count = serializers.IntegerField()


class ShiftSerializer(serializers.ModelSerializer):
    signup_stats = SignupStatsSerializer(source="get_signup_stats")
    event_title = serializers.CharField(source="event.title")

    class Meta:
        model = Shift
        fields = [
            "id",
            "event_id",
            "event_title",
            "meeting_time",
            "start_time",
            "end_time",
            "signup_flow_slug",
            "signup_flow_configuration",
            "structure_slug",
            "structure_configuration",
            "signup_stats",
        ]


class EventTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventType
        fields = ["id", "title"]


class EventSerializer(serializers.ModelSerializer):
    type = EventTypeSerializer()
    start_time = serializers.DateTimeField(source="get_start_time")
    end_time = serializers.DateTimeField(source="get_end_time")
    signup_stats = SignupStatsSerializer(source="get_signup_stats")
    shifts = ShiftSerializer(many=True)
    frontend_url = serializers.SerializerMethodField()

    def get_frontend_url(self, obj):
        return make_absolute(obj.get_absolute_url())

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "description",
            "location",
            "type",
            "frontend_url",
            "start_time",
            "end_time",
            "signup_stats",
            "shifts",
        ]


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


class ParticipationSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source="shift.event.title")
    state = ChoiceDisplayField(choices=AbstractParticipation.States.choices)
    duration = serializers.SerializerMethodField()

    class Meta:
        model = LocalParticipation
        fields = [
            "id",
            "shift",
            "event_title",
            "state",
            "comment",
            "start_time",
            "end_time",
            "duration",
            "structure_data",
        ]

    def build_unknown_field(self, field_name, model_class):
        if field_name in {"start_time", "end_time"}:
            return self.build_property_field(field_name, model_class)
        return super().build_unknown_field(field_name, model_class)

    def get_duration(self, obj):
        return (obj.end_time - obj.start_time).total_seconds()
