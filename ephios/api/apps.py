from django.apps import AppConfig


class ApiAppConfig(AppConfig):
    name = "ephios.api"

    def ready(self):
        pass
