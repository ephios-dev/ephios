from datetime import date
from django.http import JsonResponse
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET
from oauth2_provider.contrib.rest_framework import IsAuthenticatedOrTokenHasScope
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
    ParticipationSerializer,
    UserinfoParticipationSerializer,
    UserProfileSerializer,
)
from ephios.core.models import (
    AbstractParticipation,
    UserProfile,
    Qualification,
)


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


@require_GET
def calculate_expiration_date(request):
    qualification_id = request.GET.get("qualification")
    qualification_date_str = request.GET.get("qualification_date")

    # Eingaben prüfen
    if not qualification_id:
        return JsonResponse(
            {
                "error": _("No qualification selected."),
                "expiration_date": "",
            },
            status=400,
        )
    if not qualification_date_str:
        return JsonResponse(
            {
                "error": _("No qualification date provided."),
                "expiration_date": "",
            },
            status=400,
        )
    
    try:
        qualification = Qualification.objects.get(pk=qualification_id)
    except Qualification.DoesNotExist:
        return JsonResponse(
            {
                "error": _("Selected qualification does not exist."),
                "expiration_date": "",
            },
            status=400,
        )
    try:
        qualification_date = date.fromisoformat(qualification_date_str)
    except ValueError:
        return JsonResponse(
            {
                "error": _("Invalid qualification date format."),
                "expiration_date": "",
            },
            status=400,
        )
    
    # Default Expiration Time prüfen
    default_expiration = getattr(qualification, "default_expiration_time", None)
    if not default_expiration:
        return JsonResponse(
            {
                "error": _("This qualification has no default expiration time defined."),
                "expiration_date": "",
            },
            status=200,
        )

    # Ablaufdatum berechnen
    try:
        expiration_date = default_expiration.apply_to(qualification_date)
    except Exception as e:
        return JsonResponse(
            {
                "error": _("Error while calculating expiration date: %(error)s") % {"error": str(e)},
                "expiration_date": "",
            },
            status=500,
        )

    # Erfolg
    return JsonResponse(
        {
            "error": "",
            "expiration_date": expiration_date.isoformat() if expiration_date else "",
        },
        status=200,
    )