from django.apps import AppConfig
from dynamic_preferences.registries import preference_models

from ephios.event_management.registries import event_type_preference_registry


class EventManagementConfig(AppConfig):
    name = "ephios.event_management"

    def ready(self):
        from ephios.event_management import signals  # pylint: disable=unused-import

        EventTypePreference = self.get_model("EventTypePreference")
        preference_models.register(EventTypePreference, event_type_preference_registry)


default_app_config = "ephios.event_management.EventManagementConfig"
