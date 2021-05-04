from django.urls import reverse


def test_enabling_and_disabling(django_app, superuser):
    response = django_app.get(reverse("core:settings_general"), user=superuser)
    assert response
