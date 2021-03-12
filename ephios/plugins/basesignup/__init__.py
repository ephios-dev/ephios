from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from ephios.core.plugins import PluginConfig


class PluginApp(PluginConfig):
    name = "ephios.plugins.basesignup"

    class EphiosPluginMeta:
        name = _("Base Signup Plugin")
        author = "Ephios Team"
        description = _("This plugins adds basic signup methods.")

    def ready(self):
        from . import signals  # pylint: disable=unused-import


default_app_config = "ephios.plugins.basesignup.PluginApp"
