from urllib.parse import urljoin

import django_filters
import requests
from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned
from django.db.models import Max, Min
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from oauth2_provider.contrib.rest_framework import TokenHasScope
from oauthlib.oauth2 import WebApplicationClient
from requests_oauthlib import OAuth2Session
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import CreateAPIView, DestroyAPIView, ListAPIView
from rest_framework.permissions import AllowAny

from ephios.api.filters import EventFilterSet
from ephios.core.models import Event, Qualification
from ephios.plugins.federation.models import FederatedGuest, FederatedUser
from ephios.plugins.federation.serializers import (
    FederatedGuestCreateSerializer,
    SharedEventSerializer,
)


class RedeemInviteCodeView(CreateAPIView):
    """
    API view that accepts an InviteCode and creates a FederatedGuest (to start sharing events with that instance).
    """

    serializer_class = FederatedGuestCreateSerializer
    queryset = FederatedGuest.objects.all()
    authentication_classes = []
    permission_classes = [AllowAny]


class FederatedGuestDeleteView(DestroyAPIView):
    """
    API view that deletes a FederatedGuest (to stop sharing events with that instance).
    """

    queryset = FederatedGuest.objects.all()
    permission_classes = [TokenHasScope]
    required_scopes = []

    def get_object(self):
        try:
            # request.auth is an auth token, federatedguest is the reverse relation
            return self.request.auth.federatedguest
        except FederatedGuest.DoesNotExist as exc:
            raise PermissionDenied from exc


class SharedEventListView(ListAPIView):
    """
    API view that lists all events that are shared with the instance corresponding to the access token.
    """

    serializer_class = SharedEventSerializer
    permission_classes = [TokenHasScope]
    required_scopes = []
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = EventFilterSet

    def get_queryset(self):
        try:
            # request.auth is an auth token, federatedguest is the reverse relation
            guest = self.request.auth.federatedguest
        except FederatedGuest.DoesNotExist as exc:
            raise PermissionDenied from exc
        return (
            Event.objects.filter(federatedeventshare__shared_with=guest)
            .annotate(
                start_time=Min("shifts__start_time"),
                end_time=Max("shifts__end_time"),
            )
            .select_related("type")
            .prefetch_related("shifts")
            .order_by("start_time")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["federated_guest"] = self.request.auth.federatedguest
        return context


class FederationOAuthView(View):
    """
    View that handles the OAuth2 flow for federated users from another instance.
    """

    def get(self, request, *args, **kwargs):
        try:
            guest_pk = self.request.session.get("federation_guest_pk", kwargs.get("guest"))
            self.guest = FederatedGuest.objects.get(pk=guest_pk)
        except (KeyError, FederatedGuest.DoesNotExist, MultipleObjectsReturned) as exc:
            raise PermissionDenied from exc
        if "error" in request.GET.keys():
            return redirect(
                urljoin(
                    urljoin(self.guest.url, reverse("federation:external_event_list")),
                    "?error=oauth_error",
                )
            )
        elif "code" in request.GET.keys():
            self._oauth_callback()
            try:
                return redirect(
                    "federation:event_detail",
                    pk=self.request.session["federation_event"],
                    guest=guest_pk,
                )
            except KeyError:
                return redirect(
                    urljoin(
                        urljoin(self.guest.url, reverse("federation:external_event_list")),
                        "?error=event_error",
                    )
                )
        else:
            return redirect(self._get_authorization_url())

    def _get_authorization_url(self):
        oauth_client = WebApplicationClient(client_id=self.guest.client_id)
        oauth = OAuth2Session(
            client=oauth_client,
            redirect_uri=urljoin(settings.GET_SITE_URL(), reverse("federation:oauth_callback")),
            scope=["ME_READ"],
        )
        verifier = oauth_client.create_code_verifier(64)
        self.request.session["code_verifier"] = verifier
        self.request.session["federation_event"] = self.kwargs["pk"]
        self.request.session["federation_guest_pk"] = self.guest.pk
        challenge = oauth_client.create_code_challenge(verifier, "S256")
        authorization_url, _ = oauth.authorization_url(
            urljoin(self.guest.url, "api/oauth/authorize/"),
            code_challenge=challenge,
            code_challenge_method="S256",
        )
        return authorization_url

    def _oauth_callback(self):
        oauth_client = WebApplicationClient(
            client_id=self.guest.client_id, code_verifier=self.request.session["code_verifier"]
        )
        oauth = OAuth2Session(client=oauth_client)
        token = oauth.fetch_token(
            urljoin(self.guest.url, "api/oauth/token/"),
            authorization_response=urljoin(settings.GET_SITE_URL(), self.request.get_full_path()),
            client_secret=self.guest.client_secret,
            code_verifier=self.request.session["code_verifier"],
        )
        self.request.session["federation_access_token"] = token["access_token"]
        self.request.session.set_expiry(token["expires_in"])
        user_data = requests.get(
            urljoin(self.guest.url, "api/users/me/"),
            headers={"Authorization": f"Bearer {token['access_token']}"},
            timeout=5,
        )
        try:
            user = FederatedUser.objects.get(
                federated_instance=self.guest, email=user_data.json()["email"]
            )
        except FederatedUser.DoesNotExist:
            user = self._create_user(user_data.json())
        self.request.session["federated_user"] = user.pk

    def _create_user(self, user_data):
        user = FederatedUser.objects.create(
            federated_instance=self.guest,
            email=user_data["email"],
            display_name=user_data["display_name"],
            date_of_birth=user_data["date_of_birth"],
        )
        for qualification in user_data["qualifications"]:
            try:
                # Note that we assign the qualification on the host instance without further checks.
                # This may lead to incorrect qualifications if the inclusions for the qualification
                # are defined differently on the guest instance. We are accepting this as it should
                # not happen with the pre-defined qualifications as we are displaying a warning if
                # the user adapt these and custom qualifications will have different uuids anyway.
                user.qualifications.add(Qualification.objects.get(uuid=qualification["uuid"]))
            except Qualification.DoesNotExist:
                for included_qualification in qualification["includes"]:
                    try:
                        user.qualifications.add(
                            Qualification.objects.get(uuid=included_qualification)
                        )
                    except Qualification.DoesNotExist:
                        continue
        return user
