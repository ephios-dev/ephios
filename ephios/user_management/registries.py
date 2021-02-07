from dynamic_preferences.registries import PerInstancePreferenceRegistry


class EventTypeRegistry(PerInstancePreferenceRegistry):
    pass


event_type_preference_registry = EventTypeRegistry()
