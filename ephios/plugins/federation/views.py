from urllib.parse import urljoin

from django.conf import settings
from oauth2_provider.contrib.rest_framework import TokenHasScope
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListAPIView

from ephios.api.views.events import EventSerializer
from ephios.core.models import Event
from ephios.plugins.federation.models import FederatedGuest


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
        return urljoin(settings.GET_SITE_URL(), obj.get_absolute_url())


class SharedEventListView(ListAPIView):
    serializer_class = SharedEventSerializer
    permission_classes = [TokenHasScope]
    required_scopes = ["PUBLIC_READ"]

    def get_queryset(self):
        try:
            guest = self.request.auth.federatedguest_set.get()
        except FederatedGuest.DoesNotExist:
            raise PermissionDenied
        return Event.objects.filter(federatedeventshare__shared_with=guest)
