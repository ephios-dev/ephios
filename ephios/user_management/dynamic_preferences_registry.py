from django.utils.translation import gettext_lazy as _
from dynamic_preferences.preferences import Section
from dynamic_preferences.types import BooleanPreference
from dynamic_preferences.users.registries import user_preferences_registry

notifications = Section("notifications")


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
