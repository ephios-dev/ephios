from django.db.models.signals import post_save
from django.dispatch import receiver

from ephios.user_management import mail
from ephios.user_management.consequences import (
    QualificationConsequenceHandler,
    WorkingHoursConsequenceHandler,
    register_consequence_handlers,
)
from ephios.user_management.models import LocalParticipation


@receiver(
    register_consequence_handlers,
    dispatch_uid="ephios.user_management.signals.register_base_consequence_handlers",
)
def register_base_consequence_handlers(sender, **kwargs):
    return [WorkingHoursConsequenceHandler, QualificationConsequenceHandler]


@receiver(
    post_save,
    sender=LocalParticipation,
    dispatch_uid="ephios.user_management.signals.send_participation_state_changed_mail",
)
def send_participation_state_changed_mail(sender, instance, **kwargs):
    mail.participation_state_changed(instance)
