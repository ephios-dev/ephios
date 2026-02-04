from django_filters.rest_framework import DjangoFilterBackend
from oauth2_provider.contrib.rest_framework import IsAuthenticatedOrTokenHasScope, TokenHasScope
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import SearchFilter
from rest_framework.generics import RetrieveAPIView
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet

from ephios.api.filters import (
    ParticipationFilterSet,
    ParticipationPermissionFilter,
    UserinfoParticipationPermissionFilter,
)
from ephios.api.permissions import (
    ViewObjectPermissions,
    ViewPermissions,
    ViewUserModelObjectPermissions,
)
from ephios.api.serializers import (
    ConsequenceSerializer,
    ParticipationSerializer,
    UserinfoParticipationSerializer,
    UserProfileSerializer,
    WorkingHoursSerializer,
)
from ephios.core.models import AbstractParticipation, UserProfile, WorkingHours
from ephios.plugins.federation.models import FederatedConsequence, FederatedGuest


class UserProfileMeView(RetrieveAPIView):
    serializer_class = UserProfileSerializer
    queryset = UserProfile.objects.all()
    permission_classes = [IsAuthenticatedOrTokenHasScope]
    required_scopes = ["ME_READ"]

    def get_object(self):
        if self.request.user is None:
            raise PermissionDenied()
        return self.request.user


class OwnParticipationsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserinfoParticipationSerializer
    permission_classes = [IsAuthenticatedOrTokenHasScope]
    filter_backends = [UserinfoParticipationPermissionFilter, DjangoFilterBackend]
    filterset_class = ParticipationFilterSet
    required_scopes = ["ME_READ"]

    def get_queryset(self):
        return AbstractParticipation.objects.filter(
            localparticipation__user_id=self.request.user.id
        ).select_related("shift", "shift__event", "shift__event__type")


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserProfileSerializer
    queryset = UserProfile.objects.all()
    permission_classes = [IsAuthenticatedOrTokenHasScope, ViewObjectPermissions]
    required_scopes = ["CONFIDENTIAL_READ"]
    search_fields = ["display_name", "email"]

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
    ]


class UserByMailView(RetrieveModelMixin, GenericViewSet):
    serializer_class = UserProfileSerializer
    queryset = UserProfile.objects.all()
    permission_classes = [IsAuthenticatedOrTokenHasScope, ViewPermissions]
    required_scopes = ["CONFIDENTIAL_READ"]
    lookup_url_kwarg = "email"
    lookup_field = "email"
    lookup_value_regex = "[^/]+"  # customize to allow dots (".") in the lookup value


class UserParticipationView(viewsets.ReadOnlyModelViewSet):
    serializer_class = ParticipationSerializer
    permission_classes = [IsAuthenticatedOrTokenHasScope, ViewUserModelObjectPermissions]
    filter_backends = [ParticipationPermissionFilter, DjangoFilterBackend]
    filterset_class = ParticipationFilterSet
    required_scopes = ["CONFIDENTIAL_READ"]

    def get_queryset(self):
        return AbstractParticipation.objects.filter(
            localparticipation__user=self.kwargs.get("user")
        ).select_related("shift", "shift__event", "shift__event__type")


class WorkingHoursViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WorkingHoursSerializer
    permission_classes = [IsAuthenticatedOrTokenHasScope, ViewObjectPermissions]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["user", "date"]
    required_scopes = ["CONFIDENTIAL_READ"]
    queryset = WorkingHours.objects.all()


class ConsequenceViewSet(viewsets.ModelViewSet):
    serializer_class = ConsequenceSerializer
    permission_classes = [TokenHasScope]
    required_scopes = []
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["slug", "state"]

    def get_queryset(self):
        try:
            # request.auth is an auth token, federatedguest is the reverse relation
            guest = self.request.auth.federatedguest
        except (AttributeError, FederatedGuest.DoesNotExist) as exc:
            raise PermissionDenied from exc
        return FederatedConsequence.objects.filter(federated_user__federated_instance=guest)
