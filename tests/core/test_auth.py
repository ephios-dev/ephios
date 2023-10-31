from importlib import import_module
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import Group
from django.http import HttpRequest
from django.urls import reverse


@patch("ephios.extra.auth.OAuth2Session")
@patch("ephios.extra.auth.EphiosOIDCAB.decode_jwt_token")
def test_oidc_backend_authenticate(
    mock_jwt_decode, MockOAuth2Session, django_app, oidc_client, volunteer
):
    # mock all external requests
    from ephios.extra.auth import EphiosOIDCAB

    MockOAuth2Session().fetch_token.return_value = {"email": volunteer.email, "id_token": "123"}
    MockOAuth2Session().request().json.return_value = {"email": volunteer.email}

    # setup request
    request = HttpRequest()
    request.session = {"oidc_provider": oidc_client.id}
    request.GET = {"code": "123"}

    # authenticate the volunteer
    user = EphiosOIDCAB().authenticate(request)
    assert user == volunteer


def test_oidc_backend_create_user(oidc_client, groups):
    from ephios.extra.auth import EphiosOIDCAB

    managers, planners, volunteers = groups
    claims = {
        "email": "test@localhost",
        "name": "Test User",
        "phone_number": "12345",
        "birthdate": "2000-01-01",
    }
    oidc_client.default_groups.set([volunteers])
    backend = EphiosOIDCAB()
    backend.provider = oidc_client
    user = backend.create_user(claims)
    assert user.email == claims["email"]
    assert user.display_name == claims["name"]
    assert user.phone == claims["phone_number"]
    assert user.date_of_birth.isoformat() == claims["birthdate"]
    assert user.groups.count() == 1


def test_oidc_initiate(django_app, oidc_client):
    response = django_app.get(reverse("core:oidc_initiate", kwargs={"provider": oidc_client.id}))
    assert response.status_code == 302
    assert response.url.startswith(oidc_client.authorization_endpoint)


@patch("ephios.extra.auth.EphiosOIDCAB")
def test_oidc_callback(MockEphiosOIDCAB, django_app, oidc_client, volunteer):
    session = django_app.session or import_module(settings.SESSION_ENGINE).SessionStore()
    session["oidc_provider"] = oidc_client.id
    session["oidc_state"] = "123"
    session.save()
    django_app.set_cookie(settings.SESSION_COOKIE_NAME, session.session_key)
    MockEphiosOIDCAB().authenticate.return_value = volunteer
    response = django_app.get(reverse("core:oidc_callback"), params={"code": "123", "state": "123"})
    assert response.status_code == 302


def test_assign_default_groups(oidc_client, groups, volunteer):
    from ephios.extra.auth import EphiosOIDCAB

    managers, planners, volunteers = groups
    claims = {"email": volunteer.email}
    oidc_client.default_groups.set([managers])
    assert not volunteer.groups.filter(pk=managers.pk).exists()
    backend = EphiosOIDCAB()
    backend.provider = oidc_client
    volunteer = backend.update_user(volunteer, claims)
    assert volunteer.groups.filter(pk=managers.pk).exists()


def test_assign_groups_from_oidc_simple(oidc_client, groups, volunteer):
    from ephios.extra.auth import EphiosOIDCAB

    managers, planners, volunteers = groups
    claims = {"email": volunteer.email, "roles": [managers.name]}
    oidc_client.group_claim = "roles"
    assert not volunteer.groups.filter(pk=managers.pk).exists()
    backend = EphiosOIDCAB()
    backend.provider = oidc_client
    volunteer = backend.update_user(volunteer, claims)
    assert set(volunteer.groups.all()) == {managers}


def test_assign_groups_from_oidc_nested(oidc_client, groups, volunteer):
    from ephios.extra.auth import EphiosOIDCAB

    managers, planners, volunteers = groups
    claims = {"email": volunteer.email, "nested": {"roles": {"inside": [managers.name]}}}
    oidc_client.group_claim = "nested.roles.inside"
    assert not volunteer.groups.filter(pk=managers.pk).exists()
    backend = EphiosOIDCAB()
    backend.provider = oidc_client
    volunteer = backend.update_user(volunteer, claims)
    assert set(volunteer.groups.all()) == {managers}


def test_create_groups_from_oidc(oidc_client, volunteer):
    from ephios.extra.auth import EphiosOIDCAB

    claims = {"email": volunteer.email, "roles": ["test"]}
    oidc_client.group_claim = "roles"
    oidc_client.create_missing_groups = True
    assert not Group.objects.filter(name="test").exists()
    backend = EphiosOIDCAB()
    backend.provider = oidc_client
    volunteer = backend.update_user(volunteer, claims)
    assert volunteer.groups.filter(name="test").exists()


def test_assign_oidc_and_default_groups(oidc_client, groups, volunteer):
    from ephios.extra.auth import EphiosOIDCAB

    managers, planners, volunteers = groups
    claims = {"email": volunteer.email, "roles": [planners.name]}
    oidc_client.group_claim = "roles"
    oidc_client.default_groups.set([managers])
    assert not volunteer.groups.filter(pk=managers.pk).exists()
    assert not volunteer.groups.filter(pk=planners.pk).exists()
    backend = EphiosOIDCAB()
    backend.provider = oidc_client
    volunteer = backend.update_user(volunteer, claims)
    assert set(volunteer.groups.all()) == {managers, planners}
