from django.apps import AppConfig


class ApiAppConfig(AppConfig):
    name = "ephios.api"

    def ready(self):
        from . import signals  # pylint: disable=unused-import
