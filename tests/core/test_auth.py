from importlib import import_module
from unittest.mock import patch

from django.conf import settings
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
    request.session = {"oidc_client_id": oidc_client.id}
    request.GET = {"code": "123"}

    # authenticate the volunteer
    user = EphiosOIDCAB().authenticate(request)
    assert user == volunteer


def test_oidc_initiate(django_app, oidc_client):
    response = django_app.get(reverse("core:oidc_initiate", kwargs={"client": oidc_client.id}))
    assert response.status_code == 302
    assert response.url.startswith(oidc_client.auth_endpoint)


@patch("ephios.extra.auth.EphiosOIDCAB")
def test_oidc_callback(MockEphiosOIDCAB, django_app, oidc_client, volunteer):
    session = django_app.session or import_module(settings.SESSION_ENGINE).SessionStore()
    session["oidc_client_id"] = oidc_client.id
    session["oidc_state"] = "123"
    session.save()
    django_app.set_cookie(settings.SESSION_COOKIE_NAME, session.session_key)
    MockEphiosOIDCAB().authenticate.return_value = volunteer
    response = django_app.get(reverse("core:oidc_callback"), params={"code": "123", "state": "123"})
    assert response.status_code == 302
