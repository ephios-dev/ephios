import secrets
from urllib.parse import urljoin

from django.conf import settings
from django.urls import reverse
from dynamic_preferences.registries import global_preferences_registry
from rest_framework import serializers

from ephios.api.models import AccessToken
from ephios.api.views.events import EventSerializer
from ephios.core.models import Event
from ephios.plugins.federation.models import FederatedGuest, InviteCode


class FederatedGuestCreateSerializer(serializers.ModelSerializer):
    code = serializers.CharField(write_only=True)
    access_token = serializers.SlugRelatedField(slug_field="token", read_only=True)
    host_name = serializers.SerializerMethodField(method_name="get_host_name", read_only=True)

    class Meta:
        model = FederatedGuest
        fields = [
            "id",
            "name",
            "url",
            "client_id",
            "client_secret",
            "code",
            "access_token",
            "host_name",
        ]

    def get_host_name(self, obj):
        return global_preferences_registry.manager()["general__organization_name"]

    def validate(self, attrs):
        try:
            attrs["code"] = InviteCode.objects.get(code=attrs["code"], url=attrs["url"])
            if attrs["code"].is_expired:
                raise serializers.ValidationError("Invite code is expired")
            return attrs
        except InviteCode.DoesNotExist as exc:
            raise serializers.ValidationError("Invite code is not valid") from exc

    def create(self, validated_data):
        code = validated_data.pop("code")
        validated_data["access_token"] = AccessToken.objects.create(
            token=secrets.token_hex(),
            description=f"Access token for federated guest {validated_data['name']}",
        )
        obj = super().create(validated_data)
        code.delete()
        return obj


class SharedEventSerializer(EventSerializer):
    signup_url = serializers.SerializerMethodField()

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
            "signup_url",
        ]

    def get_signup_url(self, obj):
        return urljoin(
            settings.GET_SITE_URL(),
            reverse(
                "federation:event_detail",
                kwargs={"pk": obj.pk, "guest": self.context["federated_guest"].pk},
            ),
        )
