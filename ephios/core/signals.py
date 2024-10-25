from django.dispatch import receiver
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from ephios.core.plugins import PluginSignal
from ephios.core.services.notifications.backends import send_all_notifications
from ephios.core.services.participation import send_participation_finished

html_head = PluginSignal()
"""
This signal allows you to put code inside the HTML ``<head>`` tag
of every page. You will get the request as the keyword argument
``request`` and are expected to return HTML.
"""

register_consequence_handlers = PluginSignal()
"""
This signal is sent out to get all known consequence handlers. Receivers should return a list of
subclasses of ``ephios.core.consequences.BaseConsequenceHandler``.
"""

register_shift_structures = PluginSignal()
"""
This signal is sent out to get all known shift structures. Receivers should return a list of
subclasses of ``ephios.core.signup.structure.abstract.AbstractShiftStructure``.
"""

register_signup_flows = PluginSignal()
"""
This signal is sent out to get all known signup flows. Receivers should return a list of
subclasses of ``ephios.core.signup.flow.abstract.AbstractSignupFlow``.
"""

participant_signup_checkers = PluginSignal()
"""
This signal is sent out so receivers can prevent signup for a shift or provide feedback for dispatchers.
Receivers are expected to return a list of functions receiving a ``method`` and ``participant`` argument
and optionally raising fitting subclasses of ``ephios.core.signup.checkers.SignupActionError``.
"""

footer_link = PluginSignal()
"""
This signal is sent out to get links for that page footer. Receivers should return a dict of
with keys being the text and values being the url to link to.
Receivers will receive a ``request`` keyword argument.
"""

nav_link = PluginSignal()
"""
This signal is sent out to get links for the main navbar. Receivers should return a list of dicts
containing key-value-pairs for 'label', 'url' and a boolean flag 'active'. An optional key 'group' can
contain a label for a group under which the link should be displayed.
Receivers will receive a ``request`` keyword argument.
"""

management_settings_sections = PluginSignal()
"""
This signal is sent out to get sections for management settings. Receivers should return a list of dicts
containing key-value-pairs for 'label', 'url' and a boolean flag 'active'. Only views that the current user is
allowed to view should be returned. Receivers will receive a ``request`` keyword argument.
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
You receive an `Optional[event]` and `request` keyword arg you should use to create an instance of your form.
Subclass :py:class:`ephios.core.forms.events.BasePluginFormMixin` to customize the rendering behavior.
If all forms are valid, `save` will be called on your form.
"""

event_info = PluginSignal()
"""
This signal is sent out to get additional information to display in the general section of the event
detail view. Receivers will receive an `event` and `request` keyword arg to generate the information.
Receivers should return html that is added below the event description.
"""

shift_info = PluginSignal()
"""
This signal is sent out to get additional information to display in the shift box of the event
detail view. Receivers will receive a `shift` and `request` keyword arg to generate the information.
Receivers should return html that is added below the participations.
"""

shift_forms = PluginSignal()
"""
This signal is sent out to get a list of form instances to show on the shift create and update views.
You receive a `shift` and `request` keyword arg you should use to create an instance of your form.
Subclass :py:class:`ephios.core.forms.events.BasePluginFormMixin` to customize the rendering behavior.
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

register_healthchecks = PluginSignal()
"""
This signal is sent out to get all health checks that can be run to monitor the health of the application.
Receivers should return a list of subclasses of ``ephios.core.services.health.AbstractHealthCheck``
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

event_action = PluginSignal()
"""
This signal is sent out to get a list of actions that a user can perform on a single event. The actions are
displayed in the dropdown menu on the event detail view.
Receivers receive a ``event`` and ``request`` keyword argument.
Each action is represented by a dict with the keys ``url``, ``label`` and ``icon``.
"""

homepage_info = PluginSignal()
"""
This signal is sent out to get additional information to display on the homepage.
Receivers receive a ``request`` keyword argument. Receivers should return html that will be rendered inside a card.
"""

register_group_permission_fields = PluginSignal()
"""
This signal is sent out to get a list of permission fields that should be displayed on the group form.
Receivers should return a list of tuples of the form ``(field_name, field)``. field must be an instance of
``ephios.extra.permissions.PermissionField``.
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


@receiver(nav_link, dispatch_uid="ephios.core.signals.register_nav_links")
def register_nav_links(sender, request, **kwargs):
    return (
        [
            {
                "label": _("Working hours"),
                "url": reverse_lazy("core:workinghours_list"),
                "active": request.resolver_match
                and request.resolver_match.url_name == "workinghours_list",
                "group": _("Management"),
            },
            {
                "label": _("Users"),
                "url": reverse_lazy("core:userprofile_list"),
                "active": request.resolver_match
                and request.resolver_match.url_name == "userprofile_list",
                "group": _("Management"),
            },
        ]
        if request.user.has_perm("core.view_userprofile")
        else []
    ) + (
        [
            {
                "label": _("Groups"),
                "url": reverse_lazy("core:group_list"),
                "active": request.resolver_match
                and request.resolver_match.url_name == "group_list",
                "group": _("Management"),
            }
        ]
        if request.user.has_perm("core.view_group")
        else []
    )


@receiver(periodic_signal, dispatch_uid="ephios.core.signals.send_notifications")
def send_notifications(sender, **kwargs):
    send_all_notifications()


@receiver(periodic_signal, dispatch_uid="ephios.core.signals.update_last_run_periodic_call")
def update_last_run_periodic_call(sender, **kwargs):
    from ephios.core.dynamic_preferences_registry import LastRunPeriodicCall

    LastRunPeriodicCall.set_last_call(timezone.now())


periodic_signal.connect(
    send_participation_finished, dispatch_uid="ephios.core.signals.send_participation_finished"
)
