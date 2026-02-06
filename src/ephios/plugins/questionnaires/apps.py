from django.utils.translation import gettext_lazy as _

from ephios.core.plugins import PluginConfig


class PluginApp(PluginConfig):
    name = "ephios.plugins.questionnaires"

    class EphiosPluginMeta:
        name = _("Questionnaires")
        author = "Lukas Radermacher and the ephios team"
        description = _("This plugin collects answers from users during sign-up.")

    def ready(self):
        from . import signals  # noqa
