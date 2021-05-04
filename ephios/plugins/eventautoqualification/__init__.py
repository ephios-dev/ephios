from django.utils.translation import gettext_lazy as _

from ephios.core.plugins import PluginConfig


class PluginApp(PluginConfig):
    name = "ephios.plugins.eventautoqualification"

    class EphiosPluginMeta:
        name = _("Automatic qualification")
        author = "Ephios Team"
        description = _(
            "This plugin lets you configure events in a way that participants automatically aquire a qualification after participating."
        )

    def ready(self):
        from . import signals  # pylint: disable=unused-import


default_app_config = "ephios.plugins.eventautoqualification.PluginApp"
