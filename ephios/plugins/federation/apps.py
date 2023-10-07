from django.utils.translation import gettext_lazy as _

from ephios.core.plugins import PluginConfig


class PluginApp(PluginConfig):
    name = "ephios.plugins.federation"

    class EphiosPluginMeta:
        name = _("Federation")
        author = "Ephios Team"
        description = _(
            "This plugins provides the possibility to share events with other ephios instances."
        )

    def ready(self):
        from . import signals  # pylint: disable=unused-import
