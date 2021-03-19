import functools
import logging

from django.apps import AppConfig, apps
from django.conf import settings
from django.dispatch import Signal, receiver
from dynamic_preferences.registries import global_preferences_registry
from dynamic_preferences.signals import preference_updated

logger = logging.getLogger(__name__)

# The plugin mechanics are heavily inspired by pretix (licenced under Apache 2.0) - Check it out!

logger.info("Installed plugins: %s", ", ".join(settings.PLUGINS))


def get_all_plugins():
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


def get_enabled_plugins():
    """
    Return a subset of all plugin meta classes - those that are enabled
    """
    enabled_plugins = global_preferences_registry.manager().get("general__enabled_plugins")
    yield from (plugin for plugin in get_all_plugins() if plugin.module in enabled_plugins)


@functools.lru_cache()
def is_receiver_path_enabled(searchpath):
    """
    Return True only if ``searchpath`` (e.g. 'ephios.plugins.basesignup.signals')
    relies in a module that is either an enabled plugin or considered ephios core.
    Uses a cache that gets reset when enabled plugins preference changes.
    """
    enabled_paths = settings.EPHIOS_CORE_MODULES + [
        plugin.module for plugin in get_enabled_plugins()
    ]
    # Not using `startwith`, as we don't want to match "ephios_foobar" against "ephios_foo"
    while True:
        if searchpath in enabled_paths:
            return True
        if len(split := searchpath.rsplit(".", 1)) > 1:
            searchpath, _ = split
        else:
            return False


@receiver(preference_updated, dispatch_uid="ephios.core.plugins.clear_receiver_path_cache")
def clear_receiver_path_cache(sender, **kwargs):
    from ephios.core.dynamic_preferences_registry import EnabledPlugins

    if kwargs.get("name") == EnabledPlugins.name:
        logger.debug(
            "Resetting plugin path cache. Now enabled: %s",
            ", ".join(str(plugin.name) for plugin in get_enabled_plugins()),
        )
        is_receiver_path_enabled.cache_clear()


class PluginSignal(Signal):
    """
    Signal that will only be send out to enabled plugins and ephios core.
    """

    def _live_receivers(self, sender):
        return filter(
            lambda rcv: is_receiver_path_enabled(rcv.__module__), super()._live_receivers(sender)
        )

    def send_to_all_plugins(self, sender, **named):
        return [
            (receiver, receiver(signal=self, sender=sender, **named))
            for receiver in super()._live_receivers(sender)
        ]


class PluginConfig(AppConfig):
    """Superclass for Plugin App Configs. Might use this in the future to implement new features."""
