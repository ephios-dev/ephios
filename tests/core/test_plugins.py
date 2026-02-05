import pytest
from django.conf import settings
from django.urls import reverse
from dynamic_preferences.registries import global_preferences_registry

from ephios.core.plugins import get_all_plugins
from ephios.plugins.pages.models import Page


def test_plugin_discovery():
    pytest.importorskip(
        "ephios_testplugin",
        reason="ephios-testplugin isn't installed, so it cannot be detected by ephios.",
    )
    # This assertion might fail if ephios-testplugin ends up in your python path but isn't properly installed
    # in your virtual env, hence it's not found through the entry point mechanism ephios uses to find plugins.
    assert any("ephios_testplugin" in plugin_path for plugin_path in settings.PLUGINS), (
        "ephios-testplugin is installed, but wasn't found by the entry point discovery"
    )

    # Now we also need to check that the correct app config is found
    # Only apps with EphiosPluginMeta will be listed here
    assert "ephios_testplugin" in [plugin.module for plugin in get_all_plugins()][4:], (
        "ephios-testplugin is not configured as a plugin"
    )


@pytest.fixture
def page():
    return Page.objects.create(
        slug="impressum",
        title="Testimpressum",
        show_in_footer=True,
    )


def test_enabling_and_disabling(django_app, planner, page):
    """
    Tests front-to-back that enabling and disabling the pages plugin results in pages being shown in the footer or not.
    """

    preferences = global_preferences_registry.manager()
    # Need to set the preferences to have a db object so the changes later on cause a cache-clear.
    original_plugins = preferences["general__enabled_plugins"] = preferences[
        "general__enabled_plugins"
    ]

    # This tests expects pages to be enabled by default
    assert "ephios.plugins.pages" in original_plugins

    response = django_app.get(reverse("core:home"), user=planner)
    assert "Testimpressum" in response

    preferences["general__enabled_plugins"] = []
    response = django_app.get(reverse("core:home"), user=planner)
    assert "Testimpressum" not in response

    preferences["general__enabled_plugins"] = original_plugins
    response = django_app.get(reverse("core:home"), user=planner)
    assert "Testimpressum" in response
