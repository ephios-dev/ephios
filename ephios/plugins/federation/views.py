import base64
import binascii
import json
import secrets
from datetime import datetime
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, TemplateView
from guardian.mixins import LoginRequiredMixin
from oauth2_provider.contrib.rest_framework import TokenHasScope
from oauthlib.oauth2 import WebApplicationClient
from requests import HTTPError, JSONDecodeError
from requests_oauthlib import OAuth2Session
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import CreateAPIView, ListAPIView

from ephios.api.models import AccessToken
from ephios.api.views.events import EventSerializer
from ephios.core.models import Event, Qualification
from ephios.core.views.signup import BaseShiftActionView
from ephios.plugins.federation.models import (
    FederatedEventShare,
    FederatedGuest,
    FederatedHost,
    FederatedUser,
    InviteCode,
)


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
            settings.GET_SITE_URL(), reverse("federation:event_detail", kwargs={"pk": obj.pk})
        )


class FederatedGuestCreateSerializer(serializers.ModelSerializer):
    code = serializers.CharField(write_only=True)
    access_token = serializers.SlugRelatedField(slug_field="token", read_only=True)

    class Meta:
        model = FederatedGuest
        fields = ["id", "name", "url", "client_id", "client_secret", "code", "access_token"]

    def validate_code(self, value):
        try:
            data = json.loads(base64.b64decode(value.encode("ascii")).decode("ascii"))
            return InviteCode.objects.get(code=data["code"], url=data["url"])
        except (binascii.Error, JSONDecodeError, KeyError, InviteCode.DoesNotExist) as exc:
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


class SharedEventListView(ListAPIView):
    serializer_class = SharedEventSerializer
    permission_classes = [TokenHasScope]
    required_scopes = ["PUBLIC_READ"]

    def get_queryset(self):
        try:
            guest = self.request.auth.federatedguest_set.get()
        except FederatedGuest.DoesNotExist as exc:
            raise PermissionDenied from exc
        return Event.objects.filter(federatedeventshare__shared_with=guest)


class IncomingSharedEventListView(LoginRequiredMixin, TemplateView):
    template_name = "federation/incoming_shared_events.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        events = []
        for host in FederatedHost.objects.all():
            try:
                r = requests.get(
                    urljoin(host.url, reverse("federation:outgoing_shared_event_list_view")),
                    headers={"Authorization": f"Bearer {host.access_token}"},
                    timeout=5,
                )
                r.raise_for_status()
                results = r.json()["results"]
                for event in results:
                    event["type"] = event["type"]["title"]
                    event["start_time"] = datetime.fromisoformat(event["start_time"])
                    event["end_time"] = datetime.fromisoformat(event["end_time"])
                    event["host"] = host.name
                events += results
            except (HTTPError, JSONDecodeError):
                continue
        events.sort(key=lambda e: e["start_time"])
        context["events"] = events
        return context


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
            redirect_uri=urljoin(settings.GET_SITE_URL(), "api/federation/oauth-callback/"),
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


class CheckFederatedAccessTokenMixin:
    def dispatch(self, request, *args, **kwargs):
        if "access_token" not in request.session.keys():
            return FederationOAuthView.as_view()(request, *args, **kwargs)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, obj):
        context = super().get_context_data()
        context["guest_url"] = FederatedGuest.objects.get(pk=self.request.session["guest"]).url
        return context


class FederatedEventDetailView(CheckFederatedAccessTokenMixin, DetailView):
    model = Event
    template_name = "federation/event_detail.html"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        try:
            guest = self.request.session["guest"]
            FederatedEventShare.objects.get(
                event=obj,
                shared_with__in=[FederatedGuest.objects.get(pk=guest)],
            )
        except (KeyError, FederatedEventShare.DoesNotExist) as exc:
            raise PermissionDenied from exc
        return obj


class FederatedUserShiftActionView(BaseShiftActionView):
    def get_participant(self):
        try:
            return FederatedUser.objects.get(
                pk=self.request.session["federated_user"]
            ).as_participant()
        except FederatedUser.DoesNotExist as e:
            raise PermissionDenied from e


class RedeemFederationInviteCodeView(CreateAPIView):
    serializer_class = FederatedGuestCreateSerializer
    queryset = FederatedGuest.objects.all()
