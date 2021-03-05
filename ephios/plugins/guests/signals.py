from django.dispatch import receiver

from ephios.core.signals import participant_from_request
from ephios.plugins.guests.models import GuestUser


@receiver(
    participant_from_request,
    dispatch_uid="ephios.plugins.guests.signals.guest_participant_from_request",
)
def guest_participant_from_request(sender, request, **kwargs):
    if token := request.resolver_match.kwargs.get("guest_access_token"):
        try:
            return GuestUser.objects.get(access_token=token).as_participant()
        except GuestUser.DoesNotExist:
            pass
