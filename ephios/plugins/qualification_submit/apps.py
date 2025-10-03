from django.utils.translation import gettext_lazy as _

from ephios.core.plugins import PluginConfig


class PluginApp(PluginConfig):
    name = "ephios.plugins.qualification_submit"

    class EphiosPluginMeta:
        name = _("Qualification Submiting")
        author = "Ben Samuelson"
        description = _("This plugins lets you a user submit a qualification request.")

    def ready(self):
        from . import signals  # pylint: disable=unused-import
