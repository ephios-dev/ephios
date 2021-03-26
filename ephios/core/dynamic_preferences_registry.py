from django.contrib.auth.models import Group
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_select2.forms import Select2MultipleWidget
from dynamic_preferences.preferences import Section
from dynamic_preferences.registries import global_preferences_registry
from dynamic_preferences.types import MultipleChoicePreference, StringPreference
from dynamic_preferences.users.registries import user_preferences_registry

import ephios
from ephios.core import event_type_preference_registry, plugins
from ephios.core.models import QualificationCategory, UserProfile
from ephios.core.services.notifications.backends import CORE_NOTIFICATION_BACKENDS
from ephios.core.services.notifications.types import CORE_NOTIFICATION_TYPES
from ephios.extra.preferences import CustomModelMultipleChoicePreference, DictPreference

notifications_user_section = Section("notifications")
responsible_notifications_user_section = Section("responsible_notifications")
general_global_section = Section("general")


@global_preferences_registry.register
class OrganizationName(StringPreference):
    name = "organization_name"
    verbose_name = _("Organization name")
    default = ""
    section = general_global_section
    required = False


@global_preferences_registry.register
class RelevantQualificationCategories(CustomModelMultipleChoicePreference):
    name = "relevant_qualification_categories"
    section = general_global_section
    model = QualificationCategory
    default = QualificationCategory.objects.none()
    verbose_name = _("Relevant qualification categories (for user list and disposition view)")
    field_kwargs = {"widget": Select2MultipleWidget}


@global_preferences_registry.register
class EnabledPlugins(MultipleChoicePreference):
    name = "enabled_plugins"
    verbose_name = _("Enabled plugins")
    default = [
        ephios.plugins.basesignup.PluginApp.__module__,
        ephios.plugins.pages.PluginApp.__module__,
    ]
    section = general_global_section
    required = False

    @staticmethod
    def get_choices():
        return [
            (plugin.module, mark_safe(f"<strong>{plugin.name}</strong>: {plugin.description}"))
            for plugin in plugins.get_all_plugins()
        ]


@user_preferences_registry.register
class NotificationPreference(DictPreference):
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
