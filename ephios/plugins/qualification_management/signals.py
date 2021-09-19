from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext as _

from ephios.core.signals import administration_settings_section


@receiver(
    administration_settings_section,
    dispatch_uid="ephios.plugins.qualification_management.signals.qualifications_settings_section",
)
def qualifications_settings_section(sender, request, **kwargs):
    return [
        {
            "label": _("Qualifications"),
            "url": reverse("qualification_management:settings_qualification_list"),
            "active": request.resolver_match.url_name.startswith("settings_qualification"),
        },
    ]
