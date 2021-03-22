from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext as _

from ephios.core.signals import administration_settings_section, footer_link
from ephios.plugins.pages.models import Page


@receiver(footer_link, dispatch_uid="ephios.plugins.pages.signals.pages_footer_links")
def pages_footer_links(sender, request, **kwargs):
    pages = Page.objects.filter(show_in_footer=True)
    if request.user.is_anonymous:
        pages = pages.filter(publicly_visible=True)
    return {page.title: reverse("pages:page_detail", kwargs=dict(slug=page.slug)) for page in pages}


@receiver(
    administration_settings_section,
    dispatch_uid="ephios.plugins.pages.signals.pages_settings_section",
)
def pages_settings_section(sender, request, **kwargs):
    return [
        {
            "label": _("Pages"),
            "url": reverse("pages:settings_page_list"),
            "active": request.resolver_match.url_name.startswith("settings_page"),
        },
    ]
