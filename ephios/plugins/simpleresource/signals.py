from django.dispatch import receiver

from ephios.core.signals import shift_info
from ephios.plugins.simpleresource.models import ResourceAllocation


@receiver(shift_info, dispatch_uid="ephios.plugins.simpleresource.signals.shift_info")
def display_shift_resources(shift, request, **kwargs):
    try:
        allocation = ResourceAllocation.objects.get(shift=shift)
        html = "<span>Allocated resources: "
        html += ", ".join(allocation.resources.values_list("title", flat=True))
        html += "</span>"
        return html
    except ResourceAllocation.DoesNotExist:
        pass
