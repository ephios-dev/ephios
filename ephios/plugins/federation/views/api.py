from urllib.parse import urljoin

import requests
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from oauth2_provider.contrib.rest_framework import TokenHasScope
from oauthlib.oauth2 import WebApplicationClient
from requests_oauthlib import OAuth2Session
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import CreateAPIView, ListAPIView

from ephios.core.models import Event, Qualification
from ephios.plugins.federation.models import FederatedGuest, FederatedUser
from ephios.plugins.federation.serializer import (
    FederatedGuestCreateSerializer,
    SharedEventSerializer,
)


class RedeemInviteCodeView(CreateAPIView):
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


class FederationOAuthView(View):
    def get(self, request, *args, **kwargs):
        if "code" not in request.GET.keys():
            try:
                return redirect(self._get_authorization_url())
            except (KeyError, FederatedGuest.DoesNotExist) as exc:
                raise PermissionDenied from exc
        else:
            self._oauth_callback()
            return redirect("federation:event_detail", pk=self.request.session.pop("event"))

    def _get_authorization_url(self):
        guest = (
            FederatedGuest.objects.get(pk=self.request.session["guest"])
            if "guest" in self.request.session.keys()
            else FederatedGuest.objects.get(url=self.request.GET["referrer"])
        )
        oauth_client = WebApplicationClient(client_id=guest.client_id)
        oauth = OAuth2Session(
            client=oauth_client,
            redirect_uri=urljoin(settings.GET_SITE_URL(), reverse("federation:oauth_callback")),
            scope=["ME_READ"],
        )
        verifier = oauth_client.create_code_verifier(64)
        self.request.session["code_verifier"] = verifier
        self.request.session["event"] = self.kwargs["pk"]
        self.request.session["guest"] = guest.pk
        challenge = oauth_client.create_code_challenge(verifier, "S256")
        authorization_url, _ = oauth.authorization_url(
            urljoin(guest.url, "api/oauth/authorize/"),
            code_challenge=challenge,
            code_challenge_method="S256",
        )
        return authorization_url

    def _oauth_callback(self):
        guest = get_object_or_404(FederatedGuest, pk=self.request.session["guest"])
        oauth_client = WebApplicationClient(
            client_id=guest.client_id, code_verifier=self.request.session["code_verifier"]
        )
        oauth = OAuth2Session(client=oauth_client)
        token = oauth.fetch_token(
            urljoin(guest.url, "api/oauth/token/"),
            authorization_response=self.request.get_full_path(),
            client_secret=guest.client_secret,
            code_verifier=self.request.session["code_verifier"],
        )
        self.request.session["access_token"] = token["access_token"]
        self.request.session.set_expiry(token["expires_in"])
        user_data = requests.get(
            urljoin(guest.url, "api/users/me/"),
            headers={"Authorization": f"Bearer {token['access_token']}"},
            timeout=5,
        )
        try:
            user = FederatedUser.objects.get(
                federated_instance=guest, email=user_data.json()["email"]
            )
        except FederatedUser.DoesNotExist:
            user = FederatedUser.objects.create(
                federated_instance=guest,
                email=user_data.json()["email"],
                first_name=user_data.json()["first_name"],
                last_name=user_data.json()["last_name"],
                date_of_birth=user_data.json()["date_of_birth"],
            )
            for qualification in user_data.json()["qualifications"]:
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
                                Qualification.objects.get(uuid=included_qualification["uuid"])
                            )
                        except Qualification.DoesNotExist:
                            continue
        self.request.session["federated_user"] = user.pk
