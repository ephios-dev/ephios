from django.dispatch import receiver

from ephios.core.plugins import PluginSignal
from ephios.core.services.notifications.backends import send_all_notifications
from ephios.core.services.participation import send_participation_finished

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
This signal is sent out to get a list of form instances to show on the event create and update views.
You receive an `event` and `request` keyword arg you should use to create an instance of your form.
Subclass `BaseEventPluginForm` to customize the rendering behavior.
If all forms are valid, `save` will be called on your form.
"""

register_notification_types = PluginSignal()
"""
This signal is sent out to get all notification types that can be sent out to a user or participant.
Receivers should return a list of subclasses of ``ephios.core.notifications.types.AbstractNotificationHandler``
"""

register_notification_backends = PluginSignal()
"""
This signal is sent out to get all backends that can handle sending out notifications.
Receivers should return a list of subclasses of ``ephios.core.notifications.backends.AbstractNotificationBackend``
"""

periodic_signal = PluginSignal()
"""
This signal is called periodically, at least every 15 minutes.
"""

participation_finished = PluginSignal()
"""
This signal is sent out once for every confirmed participation after the participation ended and
the ``finished`` flag is set to True. Changing the shift date to the future will not cause this to be called again.
Exceptions in receivers are ignored, so make sure your code is robust enough to handle errors and retry if needed.
This signal is based on ``periodic_signal`` and provides a ``participation`` keyword argument.
"""

register_event_bulk_action = PluginSignal()
"""
This signal is sent out to get a list of actions that a user can perform on a list of events.
Receivers should return a list of actions. Each action is represented by a dict with the keys ``url``, ``label`` and ``icon``.
Once the user wants to perform the action, a POST request will be issued to this URL. The ``bulk_action`` field
will contain a list of event ids on which the action should be performed.
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
    register_notification_types, dispatch_uid="ephios.core.signals.register_core_notification_types"
)
def register_core_notification_types(sender, **kwargs):
    from ephios.core.services.notifications.types import CORE_NOTIFICATION_TYPES

    return CORE_NOTIFICATION_TYPES


@receiver(
    register_notification_backends,
    dispatch_uid="ephios.core.signals.register_core_notification_backends",
)
def register_core_notification_backends(sender, **kwargs):
    from ephios.core.services.notifications.backends import CORE_NOTIFICATION_BACKENDS

    return CORE_NOTIFICATION_BACKENDS


@receiver(periodic_signal, dispatch_uid="ephios.core.signals.send_notifications")
def send_notifications(sender, **kwargs):
    send_all_notifications()


periodic_signal.connect(
    send_participation_finished, dispatch_uid="ephios.core.signals.send_participation_finished"
)
