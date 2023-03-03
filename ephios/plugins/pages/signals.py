from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext as _

from ephios.core.signals import (
    footer_link,
    management_settings_sections,
    register_group_permission_fields,
)
from ephios.extra.permissions import PermissionField
from ephios.plugins.pages.models import Page


@receiver(footer_link, dispatch_uid="ephios.plugins.pages.signals.pages_footer_links")
def pages_footer_links(sender, request, **kwargs):
    pages = Page.objects.filter(show_in_footer=True)
    if request.user.is_anonymous:
        pages = pages.filter(publicly_visible=True)
    return {page.title: reverse("pages:page_detail", kwargs={"slug": page.slug}) for page in pages}


@receiver(
    management_settings_sections,
    dispatch_uid="ephios.plugins.pages.signals.pages_settings_section",
)
def pages_settings_section(sender, request, **kwargs):
    return (
        [
            {
                "label": _("Pages"),
                "url": reverse("pages:settings_page_list"),
                "active": request.resolver_match.url_name.startswith("settings_page"),
            },
        ]
        if request.user.has_perm("pages.add_page")
        else []
    )


@receiver(
    register_group_permission_fields,
    dispatch_uid="ephios.plugins.pages.signals.group_permission_fields",
)
def pages_group_permission_fields(sender, **kwargs):
    return [
        (
            "manage_pages",
            PermissionField(
                label=_("Manage pages"),
                help_text=_("Allows to create, edit and delete pages."),
                permissions=[
                    "pages.add_page",
                    "pages.change_page",
                    "pages.delete_page",
                ],
            ),
        )
    ]
