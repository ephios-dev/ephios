from django.utils.translation import gettext_lazy as _

from ephios.core.plugins import PluginConfig


class PluginApp(PluginConfig):
    name = "ephios.plugins.qualification_management"

    class EphiosPluginMeta:
        name = _("Qualification Management")
        author = "Ephios Team"
        description = _("This plugins lets you add and edit qualifications.")

    def ready(self):
        from . import signals  # pylint: disable=unused-import
