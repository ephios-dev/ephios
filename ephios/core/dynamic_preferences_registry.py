from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.models import Group
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.timezone import make_aware
from django.utils.translation import gettext_lazy as _
from django_select2.forms import Select2MultipleWidget
from dynamic_preferences.preferences import Section
from dynamic_preferences.registries import (
    PerInstancePreferenceRegistry,
    global_preferences_registry,
)
from dynamic_preferences.types import (
    BooleanPreference,
    DateTimePreference,
    ModelMultipleChoicePreference,
    MultipleChoicePreference,
    StringPreference,
)
from dynamic_preferences.users.registries import user_preferences_registry

from ephios.core import plugins
from ephios.core.models import Qualification, UserProfile
from ephios.core.services.notifications.backends import CORE_NOTIFICATION_BACKENDS
from ephios.core.services.notifications.types import CORE_NOTIFICATION_TYPES
from ephios.extra.preferences import JSONPreference


class EventTypeRegistry(PerInstancePreferenceRegistry):
    pass


event_type_preference_registry = EventTypeRegistry()

notifications_user_section = Section("notifications")
responsible_notifications_user_section = Section("responsible_notifications")
general_global_section = Section("general")
internal_section = Section("internal")  # for settings/stats that should not be exposed to users


@global_preferences_registry.register
class OrganizationName(StringPreference):
    name = "organization_name"
    verbose_name = _("Organization display name")
    default = "ephios"
    section = general_global_section
    required = False


@global_preferences_registry.register
class HideLoginForm(BooleanPreference):
    name = "hide_login_form"
    verbose_name = _("Hide login form")
    help_text = _(
        "Hide the login form on the login page. This only takes effect if you configured at least one identity provider."
    )
    default = False
    section = general_global_section
    required = False


@global_preferences_registry.register
class LoginRedirectToSoleIndentityProvider(BooleanPreference):
    name = "login_redirect_to_sole_identity_provider"
    verbose_name = _("Directly redirect to Identity Provider")
    help_text = _(
        "If the login form is hidden and there is a single identity provider, users trying to login"
        "will be directly redirected to that identity provider. The provider must have a valid logout endpoint."
    )
    default = False
    section = general_global_section
    required = False


@global_preferences_registry.register
class EnabledPlugins(MultipleChoicePreference):
    name = "enabled_plugins"
    verbose_name = _("Enabled plugins")
    default = [
        "ephios.plugins.baseshiftstructures",
        "ephios.plugins.basesignupflows",
        "ephios.plugins.pages",
    ]
    section = general_global_section
    required = False

    @staticmethod
    def get_choices():
        return [
            (plugin.module, mark_safe(f"<strong>{plugin.name}</strong>: {plugin.description}"))
            for plugin in plugins.get_all_plugins()
            if getattr(plugin, "visible", True)
        ]


@global_preferences_registry.register
class LastRunPeriodicCall(DateTimePreference):
    NONE_VALUE = make_aware(datetime(1970, 1, 1))
    name = "last_run_periodic_call"
    verbose_name = _("Last run_periodic call")
    section = internal_section
    required = False

    def get_default(self):
        return self.NONE_VALUE

    @classmethod
    def get_last_call(cls):
        preferences = global_preferences_registry.manager()
        last_call = preferences[f"{cls.section.name}__{cls.name}"]
        if last_call == cls.NONE_VALUE:
            return None
        return last_call

    @classmethod
    def is_stuck(cls):
        last_call = cls.get_last_call()
        return last_call is None or (
            (timezone.now() - last_call) > timedelta(seconds=settings.RUN_PERIODIC_MAX_INTERVAL)
        )

    @classmethod
    def set_last_call(cls, value):
        preferences = global_preferences_registry.manager()
        preferences[f"{cls.section.name}__{cls.name}"] = value


@user_preferences_registry.register
class NotificationPreference(JSONPreference):
    name = "notifications"
    verbose_name = _("Notification preferences")
    section = notifications_user_section
    default = dict(
        zip(
            [not_type.slug for not_type in CORE_NOTIFICATION_TYPES],
            [[backend.slug for backend in CORE_NOTIFICATION_BACKENDS]]
            * len(CORE_NOTIFICATION_TYPES),
        )
    )


@event_type_preference_registry.register
class VisibleForPreference(ModelMultipleChoicePreference):
    name = "visible_for"
    verbose_name = _("Events of this type should by default be visible for")
    model = Group
    default = Group.objects.all()
    field_kwargs = {"widget": Select2MultipleWidget}


@event_type_preference_registry.register
class ResponsibleUsersPreference(ModelMultipleChoicePreference):
    name = "responsible_users"
    verbose_name = _("Users that are responsible for this event type by default")
    model = UserProfile
    default = UserProfile.objects.none()
    field_kwargs = {"widget": Select2MultipleWidget}


@event_type_preference_registry.register
class ResponsibleGroupsPreference(ModelMultipleChoicePreference):
    name = "responsible_groups"
    verbose_name = _("Groups that are responsible for this event type by default")
    model = Group
    default = Group.objects.none()
    field_kwargs = {"widget": Select2MultipleWidget}


@event_type_preference_registry.register
class GeneralRequiredQualificationPreference(ModelMultipleChoicePreference):
    name = "general_required_qualifications"
    verbose_name = _("General required qualifications for this event type")
    help_text = _(
        "These qualifications are required for all events of this event type. Users without these qualification will not be able to sign up, so make sure to use this field appropriately."
    )
    model = Qualification
    default = Qualification.objects.none()
    field_kwargs = {"widget": Select2MultipleWidget}
