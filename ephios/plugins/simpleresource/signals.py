from django.dispatch import receiver
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from ephios.core.signals import (
    HTML_SHIFT_INFO,
    insert_html,
    nav_link,
    register_group_permission_fields,
    shift_forms,
)
from ephios.extra.permissions import PermissionField
from ephios.plugins.simpleresource.forms import ResourceAllocationForm
from ephios.plugins.simpleresource.models import ResourceAllocation


@receiver(
    insert_html,
    sender=HTML_SHIFT_INFO,
    dispatch_uid="ephios.plugins.simpleresource.signals.shift_info",
)
def display_shift_resources(shift, request, **kwargs):
    try:
        allocation = ResourceAllocation.objects.get(shift=shift)
        if allocation.resources.exists():
            return render_to_string(
                "simpleresource/resource_allocations.html", {"allocation": allocation}, request
            )
    except ResourceAllocation.DoesNotExist:
        pass
    return ""


@receiver(nav_link, dispatch_uid="ephios.plugins.simpleresource.signals.nav_link")
def add_nav_link(sender, request, **kwargs):
    return (
        [
            {
                "label": _("Resources"),
                "url": reverse_lazy("simpleresource:resource_list"),
                "active": request.resolver_match
                and request.resolver_match.app_name == "simpleresource",
                "group": _("Management"),
            }
        ]
        if request.user.has_perm("simpleresource.add_resource")
        else []
    )


@receiver(shift_forms, dispatch_uid="ephios.plugins.simpleresource.signals.shift_forms")
def resource_allocation_form(sender, shift, request, **kwargs):
    return [ResourceAllocationForm(request.POST or None, shift=shift)]


@receiver(
    register_group_permission_fields,
    dispatch_uid="ephios.plugins.simpleresource.signals.register_group_permission_fields",
)
def group_permission_fields(sender, **kwargs):
    return [
        (
            "manage_resources",
            PermissionField(
                label=_("Manage Resources"),
                help_text=_(
                    "Enables this group to add resources. Resources can be attached to shifts by all planners."
                ),
                permissions=[
                    "simpleresource.add_resource",
                    "simpleresource.change_resource",
                    "simpleresource.delete_resource",
                    "simpleresource.view_resourcecategory",
                ],
            ),
        )
    ]
