from django.utils.translation import gettext_lazy as _

from ephios.core.plugins import PluginConfig


class PluginApp(PluginConfig):
    name = "ephios.plugins.qualification_requests"

    class EphiosPluginMeta:
        name = _("Qualification Requests")
        author = "Ben Samuelson"
        description = _("This plugins lets an user submit a qualification request.")

    def ready(self):
        from . import signals  # pylint: disable=unused-import
