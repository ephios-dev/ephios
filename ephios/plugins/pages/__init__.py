from django.apps import AppConfig


class PluginConfig(AppConfig):
    name = "ephios.plugins.pages"

    def ready(self):
        from ephios.plugins.pages import signals  # pylint: disable=unused-import


default_app_config = "ephios.plugins.pages.PluginConfig"
