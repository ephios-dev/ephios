from django.apps import AppConfig


class ExtraConfig(AppConfig):
    name = "ephios.extra"

    def ready(self):
        pass  # pylint: disable=unused-import
