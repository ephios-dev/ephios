from django.utils.translation import gettext_lazy as _

from ephios.core.plugins import PluginConfig


class PluginApp(PluginConfig):
    name = "ephios.plugins.eventlistquickfilters"

    class EphiosPluginMeta:
        name = _("Event List Quick Filters")
        author = "Ephios Team"
        description = _("Configure filter presets for the event list and set per-group-defaults.")

    def ready(self):
        from . import signals  # noqa
