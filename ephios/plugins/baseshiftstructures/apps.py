from django.utils.translation import gettext_lazy as _

from ephios.core.plugins import PluginConfig


class PluginApp(PluginConfig):
    name = "ephios.plugins.baseshiftstructures"

    class EphiosPluginMeta:
        name = _("Base Shift Structures")
        author = "Ephios Team"
        description = _("This plugins adds the standard shift structures.")

    def ready(self):
        from . import signals  # pylint: disable=unused-import
