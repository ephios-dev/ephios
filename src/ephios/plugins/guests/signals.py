from django.dispatch import receiver

from ephios.core.signals import event_forms, participant_from_request, register_notification_types
from ephios.plugins.guests.forms import EventAllowGuestsForm
from ephios.plugins.guests.models import GuestUser
from ephios.plugins.guests.notifications import GuestUserSignupNotification


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


@receiver(register_notification_types, dispatch_uid="guests.signals.guests_notification_types")
def register_guests_notification_types(sender, **kwargs):
    return [GuestUserSignupNotification]
