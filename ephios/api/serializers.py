from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.fields import SerializerMethodField
from rest_framework.relations import SlugRelatedField
from rest_framework.serializers import ModelSerializer

from ephios.api.fields import ChoiceDisplayField
from ephios.core.models import (
    AbstractParticipation,
    Event,
    EventType,
    Qualification,
    Shift,
    UserProfile,
)
from ephios.core.services.qualification import collect_all_included_qualifications
from ephios.core.templatetags.settings_extras import make_absolute


class QualificationSerializer(ModelSerializer):
    category = SlugRelatedField(slug_field="uuid", read_only=True)
    includes = SerializerMethodField()

    class Meta:
        model = Qualification
        fields = [
            "uuid",
            "title",
            "abbreviation",
            "category",
            "includes",
        ]

    def get_includes(self, obj):
        return [q.uuid for q in collect_all_included_qualifications(obj.includes.all())]


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


class UserProfileSerializer(ModelSerializer):
    qualifications = SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "display_name",
            "date_of_birth",
            "email",
            "qualifications",
        ]

    def get_qualifications(self, obj):
        return QualificationSerializer(
            Qualification.objects.filter(
                Q(grants__user=obj)
                & (Q(grants__expires__gte=timezone.now()) | Q(grants__expires__isnull=True))
            ),
            many=True,
        ).data


class ParticipantSerializer(serializers.Serializer):
    display_name = serializers.CharField()
    email = serializers.EmailField(allow_null=True)
    date_of_birth = serializers.DateField()
    age = serializers.IntegerField(source="get_age")
    type = serializers.SerializerMethodField()
    qualifications = QualificationSerializer(many=True)

    def get_type(self, obj):
        """return class name of dataclass"""
        return obj.__class__.__name__

    def update(self, instance, validated_data):
        raise MethodNotAllowed("update")

    def create(self, validated_data):
        raise MethodNotAllowed("create")


class AbstractParticipationSerializer(ModelSerializer):
    state = ChoiceDisplayField(choices=AbstractParticipation.States.choices)
    duration = serializers.SerializerMethodField()
    event_title = serializers.CharField(source="shift.event.title")
    event_type = EventTypeSerializer(source="shift.event.type")
    event = serializers.PrimaryKeyRelatedField(source="shift.event", read_only=True)
    user = serializers.PrimaryKeyRelatedField(read_only=True, allow_null=True)
    participant = ParticipantSerializer(read_only=True)

    def build_unknown_field(self, field_name, model_class):
        if field_name in {"start_time", "end_time"}:
            return self.build_property_field(field_name, model_class)
        return super().build_unknown_field(field_name, model_class)

    def get_duration(self, obj):
        return (obj.end_time - obj.start_time).total_seconds()

    class Meta:
        model = AbstractParticipation
        fields = [
            "id",
            "shift",
            "event",
            "event_title",
            "event_type",
            "state",
            "comment",
            "start_time",
            "end_time",
            "duration",
            "structure_data",
            "user",
            "participant",
        ]
