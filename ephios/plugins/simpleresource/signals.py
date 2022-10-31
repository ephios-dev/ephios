from django.dispatch import receiver

from ephios.core.signals import shift_info
from ephios.plugins.simpleresource.models import Resource


@receiver(shift_info, dispatch_uid="ephios.plugins.simpleresource.signals.shift_info")
def display_shift_resources(shift, request, **kwargs):
    return " ".join(Resource.objects.all().values_list("title", flat=True))
