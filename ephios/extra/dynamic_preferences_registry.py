from dynamic_preferences.registries import global_preferences_registry
from dynamic_preferences.types import StringPreference


@global_preferences_registry.register
class OrganizationName(StringPreference):
    name = "organization_name"
    default = ""
    required = False
