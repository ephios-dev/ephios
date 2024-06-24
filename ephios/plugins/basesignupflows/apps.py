from django.utils.translation import gettext_lazy as _

from ephios.core.plugins import PluginConfig


class PluginApp(PluginConfig):
    name = "ephios.plugins.basesignupflows"

    class EphiosPluginMeta:
        name = _("Base Signup Flows")
        author = "Ephios Team"
        description = _("This plugins adds the standard signup flows.")

    def ready(self):
        from . import signals  # pylint: disable=unused-import
