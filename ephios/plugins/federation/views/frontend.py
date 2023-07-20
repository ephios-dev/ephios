from datetime import datetime
from urllib.parse import urljoin

import requests
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, DetailView, FormView, TemplateView
from guardian.mixins import LoginRequiredMixin
from requests import HTTPError, JSONDecodeError, ReadTimeout
from rest_framework.exceptions import PermissionDenied

from ephios.core.models import Event
from ephios.core.views.signup import BaseShiftActionView
from ephios.extra.mixins import StaffRequiredMixin
from ephios.plugins.federation.forms import InviteCodeForm, RedeemInviteCodeForm
from ephios.plugins.federation.models import (
    FederatedEventShare,
    FederatedGuest,
    FederatedHost,
    FederatedUser,
    InviteCode,
)
from ephios.plugins.federation.views.api import FederationOAuthView


class ExternalEventListView(LoginRequiredMixin, TemplateView):
    template_name = "federation/external_event_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        events = []
        for host in FederatedHost.objects.all():
            try:
                r = requests.get(
                    urljoin(host.url, reverse("federation:shared_event_list_view")),
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


class CreateInviteCodeView(CreateView):
    model = InviteCode
    form_class = InviteCodeForm
    success_url = reverse_lazy("federation:settings")

    def get_success_url(self):
        return reverse("federation:reveal_invite_code", kwargs={"pk": self.object.pk})


class InviteCodeRevealView(StaffRequiredMixin, TemplateView):
    template_name = "federation/invitecode_reveal.html"

    def get(self, request, *args, **kwargs):
        invite = get_object_or_404(InviteCode, pk=kwargs["pk"])
        if invite.is_expired:
            messages.error(request, _("Invite code has expired."))
            return redirect("federation:settings")
        context = self.get_context_data(invite=invite, **kwargs)
        return self.render_to_response(context)


class RedeemInviteCodeView(FormView):
    form_class = RedeemInviteCodeForm
    template_name = "federation/redeem_invite_code.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if "code" in self.request.GET:
            kwargs["initial"] = {"code": self.request.GET["code"]}
        return kwargs

    def form_valid(self, form):
        messages.success(
            self.request,
            _(
                "Invite code redeemded successfully. You are now receiving events from this instance."
            ),
        )
        return redirect(reverse("federation:settings"))


class FederatedGuestDeleteView(SuccessMessageMixin, DeleteView):
    model = FederatedGuest
    success_url = reverse_lazy("federation:settings")
    success_message = _("You are no longer sharing events with this instance.")

    def form_valid(self, form):
        access_token = self.object.access_token
        response = super().form_valid(form)
        access_token.delete()
        return response


class FederatedHostDeleteView(SuccessMessageMixin, DeleteView):
    model = FederatedHost
    success_url = reverse_lazy("federation:settings")
    success_message = _("You are no longer receiving events from this instance.")

    def form_valid(self, form):
        oauth_app = self.object.oauth_application
        response = super().form_valid(form)
        oauth_app.delete()
        return response
