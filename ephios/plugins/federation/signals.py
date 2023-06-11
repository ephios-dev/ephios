from django.dispatch import receiver
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from ephios.core.signals import nav_link


@receiver(nav_link, dispatch_uid="ephios.plugins.federation.signals.nav_link")
def add_nav_link(sender, request, **kwargs):
    return [
        {
            "label": _("External events"),
            "url": reverse_lazy("federation:incoming_shared_event_list_view"),
            "active": request.resolver_match and request.resolver_match.app_name == "federation",
        }
    ]
