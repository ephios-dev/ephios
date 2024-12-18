from django.dispatch import receiver
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from ephios.core.signals import (
    nav_link,
    register_group_permission_fields,
    register_shift_structures,
)
from ephios.extra.permissions import PermissionField
from ephios.plugins.complexsignup.structure import ComplexShiftStructure
from ephios.plugins.complexsignup.views import BuildingBlockEditorView


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
        if request.user.has_perm(BuildingBlockEditorView.permission_required)
        else []
    )


@receiver(
    register_group_permission_fields,
    dispatch_uid="ephios.plugins.complexsignup.signals.register_group_permission_fields",
)
def group_permission_fields(sender, **kwargs):
    return [
        (
            "manage_complex",
            PermissionField(
                label=_("Manage Signup Blocks"),
                help_text=_(
                    "Allows this group to manage signup blocks that can be used in reusable structures and complex shift setups."
                ),
                permissions=[
                    BuildingBlockEditorView.permission_required,
                ],
            ),
        )
    ]
