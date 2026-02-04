from urllib.parse import urljoin

import requests
from django.db import transaction
from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from ephios.core.models import UserProfile
from ephios.core.models.users import AbstractConsequence, LocalConsequence
from ephios.core.signals import (
    event_forms,
    nav_link,
    participant_from_request,
    periodic_signal,
    settings_sections,
)
from ephios.core.views.settings import SETTINGS_MANAGEMENT_SECTION_KEY
from ephios.plugins.federation.forms import EventAllowFederationForm
from ephios.plugins.federation.models import FederatedHost, FederatedUser


@receiver(nav_link, dispatch_uid="ephios.plugins.federation.signals.nav_link")
def add_nav_link(sender, request, **kwargs):
    return (
        [
            {
                "label": _("External events"),
                "url": reverse("federation:external_event_list"),
                "active": request.resolver_match
                and request.resolver_match.app_name == "federation",
            }
        ]
        if FederatedHost.objects.exists()
        else []
    )


@receiver(
    participant_from_request,
    dispatch_uid="ephios.plugins.federation.signals.federated_participant_from_request",
)
def federated_participant_from_request(sender, request, **kwargs):
    if "federated_user" in request.session.keys():
        try:
            return FederatedUser.objects.get(pk=request.session["federated_user"]).as_participant()
        except FederatedUser.DoesNotExist:
            pass


@receiver(
    event_forms,
    dispatch_uid="ephios.plugins.federation.signals.federation_event_forms",
)
def guests_event_forms(sender, event, request, **kwargs):
    return [EventAllowFederationForm(request.POST or None, event=event, request=request)]


@receiver(
    settings_sections,
    dispatch_uid="ephios.plugins.federation.signals.federation_settings_section",
)
def federation_settings_section(sender, request, **kwargs):
    return (
        [
            {
                "label": _("Federation"),
                "url": reverse("federation:settings"),
                "active": request.resolver_match.app_name == "federation",
                "group": SETTINGS_MANAGEMENT_SECTION_KEY,
            },
        ]
        if request.user.is_staff
        else []
    )


@receiver(periodic_signal, dispatch_uid="ephios.plugins.federation.signals.delete_expired_invites")
def delete_expired_invites(sender, **kwargs):
    from ephios.plugins.federation.models import InviteCode

    for invite in InviteCode.objects.all():
        if invite.is_expired:
            invite.delete()


@receiver(
    periodic_signal, dispatch_uid="ephios.plugins.federation.signals.fetch_federated_consequences"
)
def fetch_federated_consequences(sender, **kwargs):
    for federated_host in FederatedHost.objects.all():
        response = requests.get(
            urljoin(federated_host.url, "api/consequences?state=confirmed"),
            headers={"Authorization": f"Bearer {federated_host.access_token}"},
        )
        response.raise_for_status()
        pending_consequences = response.json()["results"]
        for consequence in pending_consequences:
            with transaction.atomic():
                user = UserProfile.objects.get(pk=consequence["user"])
                LocalConsequence.objects.create(
                    user=user,
                    state=AbstractConsequence.States.NEEDS_CONFIRMATION,
                    slug=consequence["slug"],
                    data=consequence["data"],
                )
                response = requests.patch(
                    urljoin(federated_host.url, f"api/consequences/{consequence['id']}/"),
                    data={"state": AbstractConsequence.States.EXECUTED},
                    headers={"Authorization": f"Bearer {federated_host.access_token}"},
                )
                response.raise_for_status()
