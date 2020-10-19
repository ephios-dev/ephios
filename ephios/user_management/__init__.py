from django.apps import AppConfig


class UserManagementConfig(AppConfig):
    name = "ephios.user_management"

    def ready(self):
        from ephios.user_management import signals  # pylint: disable=unused-import


default_app_config = "ephios.user_management.UserManagementConfig"
