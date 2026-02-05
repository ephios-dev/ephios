from django.apps import AppConfig


class ExtraConfig(AppConfig):
    name = "ephios.extra"

    def ready(self):
        from . import signals  # noqa
