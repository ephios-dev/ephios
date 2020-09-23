from django.db.models.signals import post_save
from django.dispatch import receiver

from ephios.event_management.mail import participation_state_changed
from ephios.event_management.models import LocalParticipation


@receiver(
    post_save,
    sender=LocalParticipation,
    dispatch_uid="ephios.event_management.signals.send_participation_state_changed_mail",
)
def send_participation_state_changed_mail(sender, **kwargs):
    participation_state_changed(sender, **kwargs)
