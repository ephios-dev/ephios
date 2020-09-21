from django.apps import AppConfig


class ContribConfig(AppConfig):
    name = "ephios.contrib"

    def ready(self):
        from ephios.contrib import signals  # noqa


default_app_config = "ephios.contrib.ContribConfig"
