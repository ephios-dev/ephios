from typing import List

from django.apps import AppConfig, apps
from django.conf import settings


def get_all_plugins() -> List[type]:
    """
    Returns the EphiosPluginMeta classes of all plugins found in the installed Django apps.
    """
    plugins = []
    for app in apps.get_app_configs():
        if hasattr(app, "EphiosPluginMeta"):
            meta = app.EphiosPluginMeta
            meta.module = app.name
            meta.app = app
            plugins.append(meta)

    return plugins


class PluginConfig(AppConfig):
    pass
