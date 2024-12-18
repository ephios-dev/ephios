import pytest
from django.urls import reverse

from ephios.api.models import Application


def test_creating_an_oauth_application(django_app, superuser):
    response = django_app.get(reverse("api:settings-oauth-app-register"), user=superuser)
    response.form["name"] = "Test Application"
    response.form["client_type"] = "public"
    response.form["authorization_grant_type"] = "authorization-code"
    response.form["redirect_uris"] = "http://localhost:8000"
    response = response.form.submit().follow()
    assert "Test Application" in response
    assert Application.objects.count() == 1


@pytest.fixture
def application(superuser):
    return Application.objects.create(
        name="Test Application",
        client_type="public",
        authorization_grant_type="authorization-code",
        redirect_uris="http://localhost:8000",
        user=superuser,
    )


def test_deleting_oauth_application(django_app, superuser, application):
    response = django_app.get(
        reverse("api:settings-oauth-app-delete", kwargs={"pk": application.pk}), user=superuser
    )
    response = response.form.submit().follow()
    assert Application.objects.count() == 0


def test_editing_an_application(django_app, superuser, application):
    response = django_app.get(
        reverse("api:settings-oauth-app-update", kwargs={"pk": application.pk}), user=superuser
    )
    response.form["name"] = "New Name"
    response = response.form.submit().follow()
    assert "New Name" in response
    assert Application.objects.count() == 1


def test_viewing_an_application(django_app, superuser, application):
    response = django_app.get(
        reverse("api:settings-oauth-app-detail", kwargs={"pk": application.pk}), user=superuser
    )
    assert application.name in response
