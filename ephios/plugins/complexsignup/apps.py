from django.utils.translation import gettext_lazy as _

from ephios.core.plugins import PluginConfig


class PluginApp(PluginConfig):
    name = "ephios.plugins.complexsignup"

    class EphiosPluginMeta:
        name = _("Preconfigured Structures (experimental)")
        author = "Ephios Team"
        description = _(
            "This plugins adds a shift structure for which you configure reusable "
            "structures to create complex shift setups."
        )

    def ready(self):
        from . import signals  # pylint: disable=unused-import
