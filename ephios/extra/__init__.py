from django.apps import AppConfig


class ExtraConfig(AppConfig):
    name = "ephios.extra"

    def ready(self):
        from ephios.extra import signals  # pylint: disable=unused-import


default_app_config = "ephios.extra.ExtraConfig"
