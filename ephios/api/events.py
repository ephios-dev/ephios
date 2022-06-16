import django_filters
from django.db.models import Max, Min, Prefetch
from rest_framework import filters, serializers, viewsets
from rest_framework_guardian import filters as guardian_filters

from ephios.core.models import Event, EventType, Shift


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
    signup_stats = SignupStatsSerializer(source="signup_method.get_signup_stats")

    class Meta:
        model = Shift
        fields = [
            "id",
            "meeting_time",
            "start_time",
            "end_time",
            "signup_method_slug",
            "signup_configuration",
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

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "description",
            "location",
            "type",
            "start_time",
            "end_time",
            "signup_stats",
            "shifts",
        ]


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EventSerializer
    filterset_fields = ["type"]
    search_fields = ["title", "description", "location"]
    ordering_fields = ["start_time", "end_time", "title"]
    ordering = ("start_time", "end_time")

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
