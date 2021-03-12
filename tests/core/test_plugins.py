import pytest
from django.urls import reverse
from dynamic_preferences.registries import global_preferences_registry

from ephios.plugins.pages.models import Page


@pytest.fixture
def page():
    return Page.objects.create(
        slug="impressum",
        title="Testimpressum",
        show_in_footer=True,
    )


@pytest.mark.django_db
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

    response = django_app.get(reverse("core:index"), user=planner)
    assert "Testimpressum" in response

    preferences["general__enabled_plugins"] = []
    response = django_app.get(reverse("core:index"), user=planner)
    assert "Testimpressum" not in response

    preferences["general__enabled_plugins"] = original_plugins
    response = django_app.get(reverse("core:index"), user=planner)
    assert "Testimpressum" in response
