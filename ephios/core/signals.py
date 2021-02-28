from django.db.models.signals import post_save
from django.dispatch import receiver

from ephios.core import mail
from ephios.core.models import LocalParticipation
from ephios.core.plugins import PluginSignal

register_consequence_handlers = PluginSignal()
"""
This signal is sent out to get all known consequence handlers. Receivers should return a list of
subclasses of ``ephios.core.consequences.BaseConsequenceHandler``.
"""

register_signup_methods = PluginSignal()
"""
This signal is sent out to get all known signup methods. Receivers should return a list of
subclasses of ``ephios.core.signup.methods.BaseSignupMethod``.
"""

footer_link = PluginSignal()
"""
This signal is sent out to get links for that page footer. Receivers should return a dict of
with keys being the text and values being the url to link to.
"""


@receiver(
    register_consequence_handlers,
    dispatch_uid="ephios.core.signals.register_base_consequence_handlers",
)
def register_base_consequence_handlers(sender, **kwargs):
    from ephios.core.consequences import (
        QualificationConsequenceHandler,
        WorkingHoursConsequenceHandler,
    )

    return [WorkingHoursConsequenceHandler, QualificationConsequenceHandler]


@receiver(
    post_save,
    sender=LocalParticipation,
    dispatch_uid="ephios.core.signals.send_participation_state_changed_mail",
)
def send_participation_state_changed_mail(sender, instance, **kwargs):
    mail.participation_state_changed(instance)
