from django.utils.translation import gettext_lazy as _

from ephios.core.plugins import PluginConfig


class PluginApp(PluginConfig):
    name = "ephios.plugins.complexsignup"

    class EphiosPluginMeta:
        name = _("Modular Signup Requirements")
        author = "Ephios Team"
        description = _(
            "This plugins adds a signup method for which you configure reusable "
            "modules of requirements to create complex shift setups."
        )

    def ready(self):
        from . import signals  # pylint: disable=unused-import
