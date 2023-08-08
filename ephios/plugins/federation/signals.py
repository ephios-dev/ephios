from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from ephios.core.signals import (
    event_forms,
    management_settings_sections,
    nav_link,
    participant_from_request,
    periodic_signal,
)
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
    management_settings_sections,
    dispatch_uid="ephios.plugins.federation.signals.federation_settings_section",
)
def federation_settings_section(sender, request, **kwargs):
    return (
        [
            {
                "label": _("Federation"),
                "url": reverse("federation:settings"),
                "active": request.resolver_match.app_name == "federation",
            },
        ]
        if request.user.is_staff
        else []
    )


@receiver(periodic_signal, dispatch_uid="ephios.plugins.federation.signals.periodic_signal")
def delete_expired_invites(sender, **kwargs):
    from ephios.plugins.federation.models import InviteCode

    for invite in InviteCode.objects.all():
        if invite.is_expired:
            invite.delete()
