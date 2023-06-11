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
from rest_framework.generics import ListAPIView

from ephios.api.views.events import EventSerializer
from ephios.core.models import Event
from ephios.core.views.signup import BaseShiftActionView
from ephios.plugins.federation.models import (
    FederatedEventShare,
    FederatedGuest,
    FederatedHost,
    FederatedUser,
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
                )
                r.raise_for_status()
                events += r.json()["results"]
            except (HTTPError, JSONDecodeError):
                continue
        context["events"] = events
        return context


class FederationOAuthView(View):
    def get(self, request, *args, **kwargs):
        if "code" not in request.GET.keys():
            try:
                guest = (
                    FederatedGuest.objects.get(pk=request.session["guest"])
                    if "guest" in request.session.keys()
                    else FederatedGuest.objects.get(url=request.GET["referrer"])
                )
                oauth_client = WebApplicationClient(client_id=guest.client_id)
                oauth = OAuth2Session(
                    client=oauth_client,
                    redirect_uri=urljoin(
                        settings.GET_SITE_URL(), f"api/federation/oauth-callback/"
                    ),
                    scope=["ME_READ"],
                )
                verifier = oauth_client.create_code_verifier(64)
                request.session["code_verifier"] = verifier
                request.session["event"] = self.kwargs["pk"]
                request.session["guest"] = guest.pk
                challenge = oauth_client.create_code_challenge(verifier, "S256")
                authorization_url, state = oauth.authorization_url(
                    urljoin(guest.url, "api/oauth/authorize/"),
                    code_challenge=challenge,
                    code_challenge_method="S256",
                )
                return redirect(authorization_url)
            except (KeyError, FederatedGuest.DoesNotExist):
                raise PermissionDenied
        else:
            guest = get_object_or_404(FederatedGuest, pk=request.session["guest"])
            oauth_client = WebApplicationClient(
                client_id=guest.client_id, code_verifier=request.session["code_verifier"]
            )
            oauth = OAuth2Session(client=oauth_client)
            token = oauth.fetch_token(
                urljoin(guest.url, "api/oauth/token/"),
                authorization_response=request.get_full_path(),
                client_secret=guest.client_secret,
                code_verifier=request.session["code_verifier"],
            )
            request.session["access_token"] = token["access_token"]
            user_data = requests.get(
                urljoin(guest.url, "api/users/me/"),
                headers={"Authorization": f"Bearer {token['access_token']}"},
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
            request.session["federated_user"] = user.pk
            requested_event = self.request.session.pop("event")
            return redirect("federation:event_detail", pk=requested_event)


class CheckFederatedAccessTokenMixin:
    def dispatch(self, request, *args, **kwargs):
        if "access_token" not in request.session.keys():
            return FederationOAuthView.as_view()(request, *args, **kwargs)
        else:
            try:
                guest = FederatedGuest.objects.get(pk=request.session["guest"])
                test_query = requests.get(
                    urljoin(guest.url, "api/users/me/"),
                    headers={"Authorization": f"Bearer {request.session['access_token']}"},
                )
                test_query.raise_for_status()
            except HTTPError:
                request.session.pop("access_token")
                return FederationOAuthView.as_view()(request)
            except FederatedGuest.DoesNotExist:
                raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, object):
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
        except (KeyError, FederatedEventShare.DoesNotExist):
            raise PermissionDenied
        return obj


class FederatedUserShiftActionView(BaseShiftActionView):
    def get_participant(self):
        try:
            return FederatedUser.objects.get(
                pk=self.request.session["federated_user"]
            ).as_participant()
        except FederatedUser.DoesNotExist as e:
            raise PermissionDenied from e
