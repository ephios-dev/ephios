from django.apps import AppConfig
from dynamic_preferences.registries import preference_models


class CoreAppConfig(AppConfig):
    name = "ephios.core"

    def ready(self):
        from ephios.core.dynamic_preferences_registry import event_type_preference_registry

        from . import signals  # pylint: disable=unused-import

        EventTypePreference = self.get_model("EventTypePreference")
        preference_models.register(EventTypePreference, event_type_preference_registry)
