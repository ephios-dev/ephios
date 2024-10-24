from django.db.models import Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from oauth2_provider.contrib.rest_framework import IsAuthenticatedOrTokenHasScope
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.fields import SerializerMethodField
from rest_framework.filters import SearchFilter
from rest_framework.generics import RetrieveAPIView
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.relations import SlugRelatedField
from rest_framework.serializers import ModelSerializer
from rest_framework.viewsets import GenericViewSet

from ephios.api.filters import ParticipationFilterSet, ParticipationPermissionFilter
from ephios.api.permissions import ViewPermissions
from ephios.api.views.events import ParticipationSerializer
from ephios.core.models import LocalParticipation, Qualification, UserProfile
from ephios.core.services.qualification import collect_all_included_qualifications


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
    serializer_class = ParticipationSerializer
    permission_classes = [IsAuthenticatedOrTokenHasScope]
    filter_backends = [ParticipationPermissionFilter, DjangoFilterBackend]
    filterset_class = ParticipationFilterSet
    required_scopes = ["CONFIDENTIAL_READ"]

    def get_queryset(self):
        return LocalParticipation.objects.filter(user=self.kwargs.get("user")).select_related(
            "shift", "shift__event", "shift__event__type"
        )
