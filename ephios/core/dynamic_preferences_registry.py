from django.contrib.auth.models import Group
from django.forms import CheckboxSelectMultiple
from django.utils.translation import gettext_lazy as _
from django_select2.forms import Select2MultipleWidget
from dynamic_preferences.preferences import Section
from dynamic_preferences.types import BooleanPreference
from dynamic_preferences.users.registries import user_preferences_registry

from ephios.core.models import EventType, UserProfile
from ephios.core.registries import event_type_preference_registry
from ephios.extra.preferences import CustomModelMultipleChoicePreference

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
class ResponsibleRequestedParticipationNotification(CustomModelMultipleChoicePreference):
    name = "requested_participation"
    verbose_name = _(
        "Receive notifications when a user requests a particpation for the following event types:"
    )
    section = responsible_notifications
    model = EventType
    default = EventType.objects.all()
    field_kwargs = {"widget": CheckboxSelectMultiple}


@user_preferences_registry.register
class ResponsibleRejectedParticipationNotification(CustomModelMultipleChoicePreference):
    name = "rejected_participation"
    verbose_name = _(
        "Receive notifications when a confirmed user rejects a particpation for the following event types:"
    )
    section = responsible_notifications
    model = EventType
    default = EventType.objects.all()
    field_kwargs = {"widget": CheckboxSelectMultiple}


@event_type_preference_registry.register
class VisibleForPreference(CustomModelMultipleChoicePreference):
    name = "visible_for"
    verbose_name = _("Events of this type should by default be visible for")
    model = Group
    default = Group.objects.all()
    field_kwargs = {"widget": Select2MultipleWidget}


@event_type_preference_registry.register
class ResponsibleUsersPreference(CustomModelMultipleChoicePreference):
    name = "responsible_users"
    verbose_name = _("Users that are responsible for this event type by default")
    model = UserProfile
    default = UserProfile.objects.none()
    field_kwargs = {"widget": Select2MultipleWidget}


@event_type_preference_registry.register
class ResponsibleGroupsPreference(CustomModelMultipleChoicePreference):
    name = "responsible_groups"
    verbose_name = _("Groups that are responsible for this event type by default")
    model = Group
    default = Group.objects.none()
    field_kwargs = {"widget": Select2MultipleWidget}
