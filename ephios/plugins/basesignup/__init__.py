from django.apps import AppConfig


class PluginConfig(AppConfig):
    name = "ephios.plugins.basesignup"

    def ready(self):
        from ephios.plugins.basesignup import signals


default_app_config = "ephios.plugins.basesignup.PluginConfig"
