from datetime import datetime
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, FormView, TemplateView
from guardian.mixins import LoginRequiredMixin
from oauthlib.oauth2 import WebApplicationClient
from requests import HTTPError, JSONDecodeError, ReadTimeout
from requests_oauthlib import OAuth2Session
from rest_framework.exceptions import PermissionDenied

from ephios.core.models import Event, Qualification
from ephios.core.views.signup import BaseShiftActionView
from ephios.plugins.federation.forms import InviteCodeForm, RedeemInviteCodeForm
from ephios.plugins.federation.models import (
    FederatedEventShare,
    FederatedGuest,
    FederatedHost,
    FederatedUser,
    InviteCode,
)


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
            except (HTTPError, JSONDecodeError, ReadTimeout):
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


class FederationSettingsView(TemplateView):
    template_name = "federation/federation_settings.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["guests"] = FederatedGuest.objects.all()
        context["hosts"] = FederatedHost.objects.all()
        context["invites"] = InviteCode.objects.all()
        return context


class CreateInviteCodeView(SuccessMessageMixin, CreateView):
    model = InviteCode
    form_class = InviteCodeForm
    success_url = reverse_lazy("federation:settings")

    def get_success_message(self, cleaned_data):
        return f"Invite code for {cleaned_data['url']} created."


class RedeemInviteCodeView(FormView):
    form_class = RedeemInviteCodeForm
    template_name = "federation/redeem_invite_code.html"

    def form_valid(self, form):
        messages.success(self.request, "Incoming share setup was successful.")
        return redirect(reverse("federation:settings"))
