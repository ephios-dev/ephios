from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from ephios.core.plugins import PluginConfig


class PluginApp(PluginConfig):
    name = "ephios.plugins.pages"

    class EphiosPluginMeta:
        name = _("Pages Plugin")
        author = "Ephios Team"
        description = _(
            "This plugins lets you write pages with arbitrary content and link them in the site footer. Useful for legal notices."
        )

    def ready(self):
        from . import signals  # pylint: disable=unused-import


default_app_config = "ephios.plugins.pages.PluginApp"
