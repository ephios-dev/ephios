from django.dispatch import receiver

from ephios.core.signals import event_forms, participant_from_request
from ephios.plugins.guests.forms import EventAllowGuestsForm
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


@receiver(
    event_forms,
    dispatch_uid="ephios.plugins.guests.signals.guests_event_forms",
)
def guests_event_forms(sender, event, request, **kwargs):
    return [EventAllowGuestsForm(request.POST or None, event=event, request=request)]
