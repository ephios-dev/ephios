from typing import List

from django.apps import AppConfig, apps
from django.conf import settings
from django.dispatch import Signal
from dynamic_preferences.registries import global_preferences_registry

# The plugin mechanics are heavily inspired by pretix.eu - Check them out!


def get_all_plugins() -> List[type]:
    """
    Return the EphiosPluginMeta classes of all plugins found in the installed Django apps.
    """
    plugins = []
    for app in apps.get_app_configs():
        if hasattr(app, "EphiosPluginMeta"):
            meta = app.EphiosPluginMeta
            meta.module = app.name
            meta.app = app
            plugins.append(meta)
    return sorted(
        plugins,
        key=lambda m: (
            0 if m.module.startswith("ephios.") else 1,
            str(m.name).lower().replace("ephios ", ""),
        ),
    )


global_preferences = None


def get_enabled_plugins() -> List[type]:
    """
    Return a subset of all plugin meta classes - those that are enabled
    """
    global global_preferences
    global_preferences = global_preferences or global_preferences_registry.manager()
    enabled_plugins = global_preferences["general__enabled_plugins"]
    return [plugin for plugin in get_all_plugins() if plugin.module in enabled_plugins]


class PluginSignal(Signal):
    """
    Signal that will only be send out to enabled plugins.
    """

    def _live_receivers(self, sender):
        receivers = super()._live_receivers(sender)
        # Find the Django application this belongs to
        # then compare to the module attribute of enabled plugins
        # e.g. receiver with module origin 'ephios.plugins.pages.signals' will match agains the app module path 'ephios.plugins.pages'
        enabled_paths = set(
            [plugin.module for plugin in get_enabled_plugins()] + settings.EPHIOS_CORE_MODULES
        )
        for receiver in receivers:
            searchpath: str = receiver.__module__
            while searchpath:
                if searchpath in enabled_paths:
                    yield receiver
                    break
                elif "." in searchpath:
                    searchpath, _ = searchpath.rsplit(".", 1)
                else:
                    break


class PluginConfig(AppConfig):
    """Superclass for Plugin App Configs. Might use this in the future to implement new features."""
