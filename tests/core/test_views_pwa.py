import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_get_serviceworker(django_app):
    assert django_app.get(reverse("core:pwa_serviceworker"))


@pytest.mark.django_db
def test_get_manifest(django_app):
    assert django_app.get(reverse("core:pwa_manifest"))


@pytest.mark.django_db
def test_get_offline(django_app, volunteer):
    assert django_app.get(reverse("core:pwa_offline"), user=volunteer)
