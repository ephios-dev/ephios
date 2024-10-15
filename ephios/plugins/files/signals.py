from django.dispatch import receiver
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext as _

from ephios.core.signals import (
    event_forms,
    event_info,
    management_settings_sections,
    register_group_permission_fields,
)
from ephios.extra.permissions import PermissionField
from ephios.plugins.files.forms import EventAttachedDocumentForm


@receiver(
    management_settings_sections,
    dispatch_uid="ephios.plugins.pages.signals.files_settings_section",
)
def files_settings_section(sender, request, **kwargs):
    return (
        [
            {
                "label": _("Files"),
                "url": reverse("files:settings_document_list"),
                "active": request.resolver_match.url_name.startswith("settings_document"),
            },
        ]
        if request.user.has_perm("files.add_document")
        else []
    )


@receiver(
    event_forms,
    dispatch_uid="ephios.plugins.files.signals.files_event_forms",
)
def guests_event_forms(sender, event, request, **kwargs):
    return [EventAttachedDocumentForm(request.POST or None, event=event, request=request)]


@receiver(event_info, dispatch_uid="ephios.plugins.files.signals.event_info")
def display_event_files(event, request, **kwargs):
    if event.documents.exists():
        return render_to_string(
            "files/document_attachement.html", {"documents": event.documents.all()}, request
        )


@receiver(
    register_group_permission_fields,
    dispatch_uid="ephios.plugins.files.signals.register_group_permission_fields",
)
def group_permission_fields(sender, **kwargs):
    return [
        (
            "manage_files",
            PermissionField(
                label=_("Manage files"),
                help_text=_(
                    "Enables this group to upload and manage files. Files can be attached to events by all planners."
                ),
                permissions=[
                    "files.add_document",
                    "files.change_document",
                    "files.delete_document",
                ],
            ),
        )
    ]
