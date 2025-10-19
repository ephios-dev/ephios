from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext as _

from ephios.core.views.settings import (
    SETTINGS_PERSONAL_SECTION_KEY,
    SETTINGS_MANAGEMENT_SECTION_KEY
)

@receiver(
        settings_sections,
        dispatch_uid="ephios.plugins.qualification_requests.signals.add_navigation_item",
)
def add_navigation_item(sender, request, **kwargs):
    return (
        (
            [
                {
                    "label": _(" Own Qualification Requests"),
                    "url": reverse("qualification_requests:qualification_requests_list_own"),
                    "active": request.resolver_match.url_name.startswith("qualification_requests_list_own"),
                    "group": SETTINGS_PERSONAL_SECTION_KEY,
                },
            ]
        )
        + (
            [
                {
                    "label": _("Qualification Requests"),
                    "url": reverse("qualification_requests:qualification_requests_list"),
                    "active": request.resolver_match.url_name.startswith("qualification_requests_list"),
                    "group": SETTINGS_MANAGEMENT_SECTION_KEY,
                }
            ]
            if request.user.has_perm("core.view_userprofile")
            else []
        )
    )