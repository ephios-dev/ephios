from oauth2_provider.contrib.rest_framework import TokenHasScope
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import CreateAPIView, ListAPIView

from ephios.core.models import Event
from ephios.plugins.federation.models import FederatedGuest
from ephios.plugins.federation.serializer import (
    FederatedGuestCreateSerializer,
    SharedEventSerializer,
)


class RedeemFederationInviteCodeView(CreateAPIView):
    serializer_class = FederatedGuestCreateSerializer
    queryset = FederatedGuest.objects.all()
    authentication_classes = []
    permission_classes = []


class SharedEventListView(ListAPIView):
    serializer_class = SharedEventSerializer
    permission_classes = [TokenHasScope]
    required_scopes = []

    def get_queryset(self):
        try:
            guest = self.request.auth.federatedguest_set.get()
        except FederatedGuest.DoesNotExist as exc:
            raise PermissionDenied from exc
        return Event.objects.filter(federatedeventshare__shared_with=guest)
