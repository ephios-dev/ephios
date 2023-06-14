from django.dispatch import receiver
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _

from ephios.core.signals import (
    event_forms,
    management_settings_sections,
    nav_link,
    participant_from_request,
)
from ephios.plugins.federation.forms import EventAllowFederationForm
from ephios.plugins.federation.models import FederatedUser


@receiver(nav_link, dispatch_uid="ephios.plugins.federation.signals.nav_link")
def add_nav_link(sender, request, **kwargs):
    return [
        {
            "label": _("External events"),
            "url": reverse_lazy("federation:incoming_shared_event_list_view"),
            "active": request.resolver_match and request.resolver_match.app_name == "federation",
        }
    ]


@receiver(
    participant_from_request,
    dispatch_uid="ephios.plugins.federation.signals.guest_participant_from_request",
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
                "active": request.resolver_match.url_name.startswith("federaion"),
            },
        ]
        if request.user.is_staff
        else []
    )
