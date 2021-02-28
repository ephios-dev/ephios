from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from ephios.plugins import PluginConfig


class PluginApp(PluginConfig):
    name = "ephios.plugins.basesignup"

    class EphiosPluginMeta:
        name = _("Base Signup Plugin")
        author = "Ephios Team"
        description = _("This plugins adds basic signup methods.")

    def ready(self):
        from . import signals  # NOQA


default_app_config = "ephios.plugins.basesignup.PluginApp"
