from django.utils.translation import gettext_lazy as _

from ephios.core.plugins import PluginConfig


class PluginApp(PluginConfig):
    name = "ephios.plugins.files"

    class EphiosPluginMeta:
        name = _("Files")
        author = "Ephios Team"
        description = _("This plugins allows you to upload files and link to them in events.")

    def ready(self):
        from . import signals  # pylint: disable=unused-import
