from datetime import datetime, timedelta
from urllib.parse import urljoin

import requests
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, DetailView, FormView, TemplateView
from dynamic_preferences.registries import global_preferences_registry
from guardian.mixins import LoginRequiredMixin
from requests import HTTPError, JSONDecodeError, ReadTimeout
from rest_framework.exceptions import PermissionDenied

from ephios.api.models import Application
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
    """
    View that lists all events that are shared with this instance.
    """

    template_name = "federation/external_event_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        events = []
        for host in FederatedHost.objects.all():
            try:
                r = requests.get(
                    urljoin(host.url, reverse("federation:shared_event_list_view")),
                    headers={"Authorization": f"Bearer {host.access_token}"},
                    params={"end_time_after": (datetime.now() - timedelta(days=14)).isoformat()},
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
            except HTTPError as exc:
                if exc.response.status_code == 403:
                    # the host does not accept our token anymore, so the share needs to be set up again
                    host.oauth_application.delete()
                    host.delete()
            except (JSONDecodeError, ReadTimeout):
                continue
        events.sort(key=lambda e: e["start_time"])
        context["events"] = events
        return context


class CheckFederatedAccessTokenMixin:
    def dispatch(self, request, *args, **kwargs):
        if "federation_access_token" not in request.session.keys():
            return FederationOAuthView.as_view()(request, *args, **kwargs)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, object):
        context = super().get_context_data()
        context["federation_guest"] = FederatedGuest.objects.get(
            pk=self.request.session["federation_guest_pk"]
        )
        return context


class FederatedEventDetailView(CheckFederatedAccessTokenMixin, DetailView):
    """
    View that displays a shared event to a federated user from another instance
    """

    model = Event
    template_name = "federation/event_detail.html"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        try:
            FederatedEventShare.objects.get(
                event=obj,
                shared_with__in=[FederatedGuest.objects.get(pk=self.kwargs["guest"])],
            )
        except (KeyError, FederatedEventShare.DoesNotExist, FederatedGuest.DoesNotExist) as exc:
            self.request.session.flush()
            raise PermissionDenied from exc
        return obj


class FederatedUserShiftActionView(CheckFederatedAccessTokenMixin, BaseShiftActionView):
    """
    View that allows a federated user from another instanceto sign up for a shift
    """

    def get_participant(self):
        try:
            return FederatedUser.objects.get(
                pk=self.request.session["federated_user"]
            ).as_participant()
        except FederatedUser.DoesNotExist as e:
            raise PermissionDenied from e


class FederationSettingsView(StaffRequiredMixin, TemplateView):
    """
    View that displays the federation settings page where new instances can be connected
    """

    template_name = "federation/federation_settings.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["federation_guests"] = FederatedGuest.objects.all()
        context["federation_hosts"] = FederatedHost.objects.all()
        context["federation_invites"] = InviteCode.objects.all()
        return context


class CreateInviteCodeView(StaffRequiredMixin, CreateView):
    """
    View that allows staff users to create new invite codes (to share events with another instance)
    """

    model = InviteCode
    form_class = InviteCodeForm

    def get_success_url(self):
        return reverse("federation:reveal_invite_code", kwargs={"pk": self.object.pk})


class InviteCodeRevealView(StaffRequiredMixin, TemplateView):
    """
    View that displays an invite code to a staff user
    """

    template_name = "federation/invitecode_reveal.html"

    def get(self, request, *args, **kwargs):
        invite = get_object_or_404(InviteCode, pk=kwargs["pk"])
        if invite.is_expired:
            messages.error(request, _("Invite code has expired."))
            return redirect("federation:settings")
        context = self.get_context_data(invite=invite, **kwargs)
        return self.render_to_response(context)


class RedeemInviteCodeView(StaffRequiredMixin, FormView):
    """
    View that allows staff users to redeem an invite code (to receive events from another instance)
    """

    form_class = RedeemInviteCodeForm
    template_name = "federation/redeem_invite_code.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if "code" in self.request.GET:
            kwargs["initial"] = {"code": self.request.GET["code"]}
        return kwargs

    @transaction.atomic
    def _setup_federated_host(self, data):
        oauth_application = Application(
            user=self.request.user,
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
            redirect_uris=urljoin(data["host_url"], reverse("federation:oauth_callback")),
        )
        response = requests.post(
            urljoin(data["host_url"], reverse("federation:redeem_invite_code")),
            data={
                "name": global_preferences_registry.manager()["general__organization_name"],
                "url": data["guest_url"],
                "client_id": oauth_application.client_id,
                "client_secret": oauth_application.client_secret,
                "code": data["code"],
            },
            timeout=10,
        )
        response.raise_for_status()
        response_data = response.json()
        oauth_application.name = response_data["host_name"]
        oauth_application.save()
        FederatedHost.objects.create(
            name=response_data["host_name"],
            url=data["host_url"],
            access_token=response_data["access_token"],
            oauth_application=oauth_application,
        )

    def form_valid(self, form):
        try:
            self._setup_federated_host(form.code_data)
        except (KeyError, JSONDecodeError):
            messages.error(
                self.request,
                _("Invalid code data. Please try again with a new invite code."),
            )
        except (HTTPError, ReadTimeout):
            messages.error(
                self.request,
                _("Could not connect to host instance. Please try again later."),
            )
        else:
            messages.success(
                self.request,
                _(
                    "Invite code redeemded successfully. You are now receiving events from this instance."
                ),
            )
            return redirect(reverse("federation:settings"))
        return self.form_invalid(form)


class FederatedGuestDeleteView(StaffRequiredMixin, SuccessMessageMixin, DeleteView):
    """
    View that allows staff users to remove a guest instance (to stop sharing events with another instance)
    """

    model = FederatedGuest
    success_url = reverse_lazy("federation:settings")
    success_message = _("You are no longer sharing events with this instance.")

    def form_valid(self, form):
        access_token = self.object.access_token
        response = super().form_valid(form)
        access_token.delete()
        return response


class FederatedHostDeleteView(StaffRequiredMixin, SuccessMessageMixin, DeleteView):
    """
    View that allows staff users to remove a host instance (to stop receiving events from another instance)
    """

    model = FederatedHost
    success_url = reverse_lazy("federation:settings")
    success_message = _("You are no longer receiving events from this instance.")

    def form_valid(self, form):
        oauth_app = self.object.oauth_application
        guest_response = requests.delete(
            urljoin(self.object.url, reverse("federation:api_delete_guest")),
            headers={"Authorization": f"Bearer {self.object.access_token}"},
            timeout=5,
        )
        if guest_response.status_code != 204:
            messages.error(
                self.request,
                _("Failed to remove this instance. Please try again later."),
            )
            return redirect("federation:settings")
        response = super().form_valid(form)
        oauth_app.delete()
        return response
