from django.apps import AppConfig


class LoggingAppConfig(AppConfig):
    name = "ephios.modellogging"


default_app_config = "ephios.modellogging.LoggingAppConfig"
