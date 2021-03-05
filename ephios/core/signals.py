from django.db.models.signals import post_save
from django.dispatch import receiver

from ephios.core import mail
from ephios.core.models import LocalParticipation
from ephios.core.plugins import PluginSignal

# PluginSignals are only send out to enabled plugins.

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
Receivers will receive a ``request`` keyword argument.
"""

administration_settings_section = PluginSignal()
"""
This signal is sent out to get sections for administration settings. Receivers should return a list of dicts
containing key-value-pairs for 'label', 'url' and a boolean flag 'active'.
Receivers will receive a ``request`` keyword argument.
"""

participant_from_request = PluginSignal()
"""
This signal is sent out to get a participant from a request with an unauthenticated user.
Return a subclass of AbstractParticipant or None if you cannot provide a participant.
The first non-None return-value will be used.
Receivers will receive a ``request`` keyword argument.
"""

event_forms = PluginSignal()
"""
This signal...
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
