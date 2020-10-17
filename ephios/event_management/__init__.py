from django.apps import AppConfig


class EventManagementConfig(AppConfig):
    name = "ephios.event_management"

    def ready(self):
        from ephios.event_management import signals  # pylint: disable=unused-import


default_app_config = "ephios.event_management.EventManagementConfig"
