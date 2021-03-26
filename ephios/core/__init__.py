from django.apps import AppConfig
from dynamic_preferences.registries import PerInstancePreferenceRegistry, preference_models


class EventTypeRegistry(PerInstancePreferenceRegistry):
    pass


event_type_preference_registry = EventTypeRegistry()


class UserManagementConfig(AppConfig):
    name = "ephios.core"

    def ready(self):
        from . import signals  # pylint: disable=unused-import

        EventTypePreference = self.get_model("EventTypePreference")
        preference_models.register(EventTypePreference, event_type_preference_registry)


default_app_config = "ephios.core.UserManagementConfig"
