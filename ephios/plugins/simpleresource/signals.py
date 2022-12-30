from django.dispatch import receiver
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from ephios.core.signals import nav_link, shift_forms, shift_info
from ephios.plugins.simpleresource.forms import ResourceAllocationForm
from ephios.plugins.simpleresource.models import ResourceAllocation


@receiver(shift_info, dispatch_uid="ephios.plugins.simpleresource.signals.shift_info")
def display_shift_resources(shift, request, **kwargs):
    try:
        allocation = ResourceAllocation.objects.get(shift=shift)
        if allocation.resources.exists():
            html = f"<span>{_('Allocated resources:')} "
            html += ", ".join(allocation.resources.values_list("title", flat=True))
            html += "</span>"
            return mark_safe(html)
    except ResourceAllocation.DoesNotExist:
        pass


@receiver(nav_link, dispatch_uid="ephios.plugins.simpleresource.signals.nav_link")
def add_nav_link(sender, request, **kwargs):
    return [
        {
            "label": "Resources",
            "url": reverse_lazy("simpleresource:resource_list"),
            "active": request.resolver_match.url_name.startswith("simpleresource"),
        }
    ]


@receiver(shift_forms, dispatch_uid="ephios.plugins.simpleresource.signals.shift_forms")
def resource_allocation_form(sender, shift, request, **kwargs):
    return [ResourceAllocationForm(request.POST or None, shift=shift)]
