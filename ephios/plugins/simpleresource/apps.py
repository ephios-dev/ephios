from django.utils.translation import gettext_lazy as _

from ephios.core.plugins import PluginConfig


class PluginApp(PluginConfig):
    name = "ephios.plugins.simpleresource"

    class EphiosPluginMeta:
        name = _("Simple Resource Management Plugin")
        author = "Ephios Team"
        description = _("This plugins provides a simple resource management system.")

    def ready(self):
        from . import signals  # pylint: disable=unused-import
