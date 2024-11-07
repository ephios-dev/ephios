from django_filters.rest_framework import DjangoFilterBackend
from oauth2_provider.contrib.rest_framework import IsAuthenticatedOrTokenHasScope
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import SearchFilter
from rest_framework.generics import RetrieveAPIView
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet

from ephios.api.filters import AbstractParticipationFilterSet, ParticipationPermissionFilter
from ephios.api.permissions import ParticipationPermissions, ViewPermissions
from ephios.api.serializers import AbstractParticipationSerializer, UserProfileSerializer
from ephios.core.models import LocalParticipation, UserProfile


class UserProfileMeView(RetrieveAPIView):
    serializer_class = UserProfileSerializer
    queryset = UserProfile.objects.all()
    permission_classes = [IsAuthenticatedOrTokenHasScope]
    required_scopes = ["ME_READ"]

    def get_object(self):
        if self.request.user is None:
            raise PermissionDenied()
        return self.request.user


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserProfileSerializer
    queryset = UserProfile.objects.all()
    permission_classes = [IsAuthenticatedOrTokenHasScope, ViewPermissions]
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
    serializer_class = AbstractParticipationSerializer
    permission_classes = [ParticipationPermissions, IsAuthenticatedOrTokenHasScope]
    filter_backends = [ParticipationPermissionFilter, DjangoFilterBackend]
    filterset_class = AbstractParticipationFilterSet
    required_scopes = ["CONFIDENTIAL_READ"]

    def get_queryset(self):
        return LocalParticipation.objects.filter(user=self.kwargs.get("user")).select_related(
            "shift", "shift__event", "shift__event__type"
        )
