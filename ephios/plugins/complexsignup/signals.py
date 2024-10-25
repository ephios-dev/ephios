from django.dispatch import receiver
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from ephios.core.signals import nav_link, register_shift_structures
from ephios.plugins.complexsignup.structure import ComplexShiftStructure


@receiver(
    register_shift_structures,
    dispatch_uid="ephios.plugins.complexsignup.signals.register_complex_shift_structures",
)
def register_complex_shift_structures(sender, **kwargs):
    return [
        ComplexShiftStructure,
    ]


@receiver(nav_link, dispatch_uid="ephios.plugins.complexsignup.signals.nav_link")
def add_nav_link(sender, request, **kwargs):
    return (
        [
            {
                "label": _("Signup blocks"),
                "url": reverse_lazy("complexsignup:blocks_editor"),
                "active": request.resolver_match
                and request.resolver_match.app_name == "complexsignup",
                "group": _("Management"),
            }
        ]
        if request.user.has_perm("core.delete_event")
        else []
    )
