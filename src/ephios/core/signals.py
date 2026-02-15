import sys

from django.dispatch import receiver
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from ephios.core.plugins import PluginSignal
from ephios.core.services.notifications.backends import send_all_notifications
from ephios.core.services.participation import send_participation_finished

insert_html = PluginSignal()
"""
This signal allows you to put html in various places.
You will get the request as the keyword argument ``request``
and are expected to return HTML. Try to use html elements that
fit the existing document structure. Return an empty string
to not render anything.

The sender argument specifies the template location and can be one
of these constants:

- ``HTML_HEAD``: Add HTML in the <head> tag.
- ``HTML_NAVBAR``: Add HTML in the navbar.
- ``HTML_EVENT_INFO``: Add HTML to the event detail page event info box. Comes with an ``event`` kwarg.
- ``HTML_SHIFT_INFO``: Add HTML to the event detail page shift box. Comes with a ``shift`` kwarg.
- ``HTML_HOMEPAGE_INFO``: Add HTML to the homepage content area.
- ``HTML_PERSONAL_DATA_PAGE``: Add HTML to the settings "personal data" page of the logged-in user.
- ``HTML_DISPOSITION_PARTICIPATION``: Add HTML to the expandable details view of a participation form in the disposition view. Comes with a ``participation`` kwarg.
"""

HTML_HEAD = sys.intern("head")
HTML_NAVBAR = sys.intern("navbar")
HTML_EVENT_INFO = sys.intern("event_info")
HTML_SHIFT_INFO = sys.intern("shift_info")
HTML_HOMEPAGE_INFO = sys.intern("homepage_info")
HTML_PERSONAL_DATA_PAGE = sys.intern("personal_data_page")
HTML_DISPOSITION_PARTICIPATION = sys.intern("disposition_participation")


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
contain a label for a group under which the link should be displayed. The special group ``NAV_USERPROFILE_KEY``
is reserved for the group under the users name.
Receivers will receive a ``request`` keyword argument.
"""

settings_sections = PluginSignal()
"""
This signal is sent out to get sections for the settings. Receivers should return a list of dicts
containing key-value-pairs for 'label', 'url', 'group' and a boolean flag 'active'. Only views that the current user is
allowed to view should be returned. Common group choices are ``SETTINGS_PERSONAL_SECTION_KEY``
and ``SETTINGS_MANAGEMENT_SECTION_KEY`` but can be any other value as well.
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
You receive an `Optional[event]` and `request` keyword arg you should use to create an instance of your form.
Subclass :py:class:`ephios.core.forms.events.BasePluginFormMixin` to customize the rendering behavior.
If all forms are valid, `save` will be called on your form.
"""


shift_action = PluginSignal()
"""
This signal is sent out to collect additional actions that managers can perform on on a shift. For
each action, a button will be displayed in the shift card next to the disposition button. Receivers
of the signal will receive the ``shift`` and ``request`` and are expected to return an array of
``{label: str, url: str}`` dicts, representing the available actions.
The buttons will only be shown to responsibles of the respective shift.
"""

shift_copy = PluginSignal()
"""
This signal is set out after a shift got copied to allow plugins to copy related data as well.
Receivers will receive the original ``shift`` and a list of the created ``copies``.
"""

shift_forms = PluginSignal()
"""
This signal is sent out to get a list of form instances to show on the shift create and update views.
You receive a `shift` and `request` keyword arg you should use to create an instance of your form.
Subclass :py:class:`ephios.core.forms.events.BasePluginFormMixin` to customize the rendering behavior.
If all forms are valid, `save` will be called on your form.
"""

signup_form_fields = PluginSignal()
"""
This signal is sent out to get a list of form fields to show on the signup view, especially to collect
user input for shift structures. Receivers will receive the ``shift``, ``participant``, ``participation``,
and ``signup_choice`` and should return a dict in the form ``{ 'fieldname1': {
    'label':, ...,
    'help_text':, ...,
    'default': ...,
    'required': ...,  # meaning a non-Falsey value must be provided
    'form_class': ...,
    'form_kwargs': ...,
    'serializer_class': ...,
    'serializer_kwargs': ...,
    }, 'fieldname2: { ... } }``.
``label`` (only form), ``help_text`` (only form), ``default`` (only form, as ``initial``), and ``required``
(form and serializer) will be applied to the kwargs dicts for convenience. Values specified directly
as kwarg have precedence.
"""


def collect_signup_form_fields(shift, participant, participation, signup_choice):
    responses = signup_form_fields.send(
        sender=None,
        shift=shift,
        participant=participant,
        participation=participation,
        signup_choice=signup_choice,
    )
    for __, additional_fields in responses:
        for fieldname, field in additional_fields.items():
            # add some defaults to form field and serializer kwargs
            yield (
                fieldname,
                {
                    **field,
                    "form_kwargs": {
                        "label": field["label"],
                        "help_text": field.get("help_text", ""),
                        "initial": field["default"],
                        "required": field["required"],
                        **field["form_kwargs"],
                    },
                    "serializer_kwargs": {
                        "required": field["required"],
                        **field["serializer_kwargs"],
                    },
                },
            )


signup_save = PluginSignal()
"""
This signal is sent out to when a signup is created or modified to allow plugins to handle additional
user input. Receivers will receive the ``shift``, ``participant``, ``participation``, ``signup_choice``,
and ``cleaned_data``.
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

event_menu = PluginSignal()
"""
This signal is sent out to get a list of actions that a user can perform on a single event. The actions are
displayed in the dropdown menu on the event detail view.
Receivers receive a ``event`` and ``request`` keyword argument.
Each action is represented by a dict with the keys ``url``, ``label`` and ``icon``.
"""

register_group_permission_fields = PluginSignal()
"""
This signal is sent out to get a list of permission fields that should be displayed on the group form.
Receivers should return a list of tuples of the form ``(field_name, field)``. field must be an instance of
``ephios.extra.permissions.PermissionField``.
"""

oidc_update_user = PluginSignal()
"""
This signal is sent out to update a user when they login with oidc. Receivers receive ``user`` and ``claims``
keyword arguments with a user object and the claims from the oidc provider.
"""


provide_dynamic_settings = PluginSignal()
"""
Use this signal to overwrite the defaults of django settings accessed
using ``ephios.core.signals.DynamicSettingsProxy``.
Receivers receive a ``name`` keyword argument naming the setting.
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
        (
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
        )
        + (
            [
                {
                    "label": _("Groups"),
                    "url": reverse_lazy("core:group_list"),
                    "active": request.resolver_match
                    and request.resolver_match.url_name == "group_list",
                    "group": _("Management"),
                }
            ]
            if request.user.has_perm("auth.view_group")
            else []
        )
        + (
            [
                {
                    "label": _("Settings"),
                    "url": reverse_lazy("core:settings_instance"),
                    "active": request.resolver_match
                    and request.resolver_match.url_name == "settings_instance",
                    "group": _("Management"),
                }
            ]
            if request.user.is_staff
            else []
        )
    )


@receiver(periodic_signal, dispatch_uid="ephios.core.signals.send_notifications")
def send_notifications(sender, **kwargs):
    send_all_notifications()


@receiver(periodic_signal, dispatch_uid="ephios.core.signals.update_last_run_periodic_call")
def update_last_run_periodic_call(sender, **kwargs):
    from ephios.core.dynamic_preferences_registry import LastRunPeriodicCall

    LastRunPeriodicCall.set_last_call(timezone.now())


@receiver(signup_form_fields, dispatch_uid="ephios.core.signals.provide_structure_form_fields")
def provide_structure_form_fields(
    sender, shift, participant, participation, signup_choice, **kwargs
):
    return shift.structure.get_signup_form_fields(participant, participation, signup_choice)


@receiver(signup_save, dispatch_uid="ephios.core.signals.structure_signup_save")
def structure_signup_save(
    sender, shift, participant, participation, signup_choice, cleaned_data, **kwargs
):
    shift.structure.save_signup(participant, participation, signup_choice, cleaned_data)


periodic_signal.connect(
    send_participation_finished, dispatch_uid="ephios.core.signals.send_participation_finished"
)
