from django.apps import AppConfig


class ContribConfig(AppConfig):
    name = "contrib"

    def ready(self):
        from contrib import signals  # noqa


default_app_config = "contrib.ContribConfig"
