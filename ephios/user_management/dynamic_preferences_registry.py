from django.forms import CheckboxSelectMultiple
from django.utils.translation import gettext_lazy as _
from dynamic_preferences.preferences import Section
from dynamic_preferences.types import BooleanPreference, ModelMultipleChoicePreference
from dynamic_preferences.users.registries import user_preferences_registry

from ephios.event_management.models import EventType

notifications = Section("notifications")
responsible_notifications = Section("responsible_notifications")


@user_preferences_registry.register
class NewEventNotification(BooleanPreference):
    name = "new_event"
    verbose_name = _("Receive notifications for new events")
    section = notifications
    default = True


@user_preferences_registry.register
class ParticipationConfirmNotification(BooleanPreference):
    name = "confirm_participation"
    verbose_name = _("Receive notifications for a confirmed participation")
    section = notifications
    default = True


@user_preferences_registry.register
class ParticipationRejectNotification(BooleanPreference):
    name = "reject_participation"
    verbose_name = _("Receive notifications for a rejected participation")
    section = notifications
    default = True


@user_preferences_registry.register
class UserProfileUpdateNotification(BooleanPreference):
    name = "userprofile_update"
    verbose_name = _("Receive notifications for changes to your profile")
    section = notifications
    default = True


@user_preferences_registry.register
class ResponsibleRequestedParticipationNotification(ModelMultipleChoicePreference):
    name = "requested_participation"
    verbose_name = _(
        "Receive notifications when a user requests a particpation for the following event types:"
    )
    section = responsible_notifications
    model = EventType
    default = EventType.objects.all()
    field_kwargs = {"widget": CheckboxSelectMultiple}


@user_preferences_registry.register
class ResponsibleRejectedParticipationNotification(ModelMultipleChoicePreference):
    name = "rejected_participation"
    verbose_name = _(
        "Receive notifications when a confirmed user rejects a particpation for the following event types:"
    )
    section = responsible_notifications
    model = EventType
    default = EventType.objects.all()
    field_kwargs = {"widget": CheckboxSelectMultiple}
