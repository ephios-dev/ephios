from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from ephios.core.plugins import PluginConfig


class PluginApp(PluginConfig):
    name = "ephios.plugins.public_participation"

    class EphiosPluginMeta:
        name = _("Public Participations")
        author = "Ephios Team"
        description = _(
            "This plugins allows you to accept signups for individual events from people without an account, using a public signup form."
        )

    def ready(self):
        from . import signals  # pylint: disable=unused-import


default_app_config = "ephios.plugins.pages.PluginApp"
