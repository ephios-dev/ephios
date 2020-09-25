from django.dispatch import receiver
from django.urls import reverse

from ephios.extra.signals import footer_link
from ephios.plugins.pages.models import Page


@receiver(footer_link, dispatch_uid="ephios.plugins.pages.signals.pages_footer_links")
def pages_footer_links(sender, request, **kwargs):
    pages = Page.objects.filter(show_in_footer=True)
    if request.user.is_anonymous:
        pages = pages.filter(publicly_visible=True)
    return {page.title: reverse("pages:view_page", kwargs=dict(slug=page.slug)) for page in pages}
