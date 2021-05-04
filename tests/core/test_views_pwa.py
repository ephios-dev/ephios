from django.urls import reverse


def test_get_serviceworker(django_app):
    assert django_app.get(reverse("core:pwa_serviceworker"))


def test_get_manifest(django_app):
    assert django_app.get(reverse("core:pwa_manifest"))


def test_get_offline(django_app, volunteer):
    assert django_app.get(reverse("core:pwa_offline"), user=volunteer)
