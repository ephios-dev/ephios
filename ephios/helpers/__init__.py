from django.apps import AppConfig


class HelpersConfig(AppConfig):
    name = "ephios.helpers"

    def ready(self):
        from ephios.helpers import signals


default_app_config = "ephios.helpers.HelpersConfig"
