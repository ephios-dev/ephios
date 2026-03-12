from importlib import import_module
from unittest.mock import patch

from django.urls import reverse

from ephios.plugins.federation.models import FederatedParticipation, FederatedUser
from ephios.plugins.federation.serializers import SharedEventSerializer
from ephios.plugins.federation.views.api import FederationOAuthView


def test_federation_get_shared_events(django_app, volunteer, federation, federated_event):
    host, guest = federation
    response = django_app.get(
        reverse("federation:shared_event_list_view"),
        headers={"Authorization": f"Bearer {host.access_token}"},
    )
    assert federated_event.title in response.text


@patch("ephios.plugins.federation.views.frontend.requests")
def test_federation_shared_event_list(
    mock_requests, django_app, volunteer, federation, federated_event, settings
):
    host, guest = federation
    mock_requests.get.return_value.json.return_value = {
        "results": [SharedEventSerializer(federated_event, context={"federated_guest": guest}).data]
    }

    response = django_app.get(reverse("federation:external_event_list"), user=volunteer)
    assert response.status_code == 200
    assert federated_event.title in response.text


def test_federation_shared_event_detail_and_signup(
    django_app, volunteer, federation, federated_user, federated_event, settings
):
    host, guest = federation
    session = django_app.session or import_module(settings.SESSION_ENGINE).SessionStore()
    session["federation_access_token"] = "token"
    session["federation_guest_pk"] = guest.pk
    session["federated_user"] = federated_user.pk
    session.save()
    django_app.set_cookie(settings.SESSION_COOKIE_NAME, session.session_key)

    response = django_app.get(
        reverse("federation:event_detail", kwargs={"pk": federated_event.pk, "guest": guest.pk})
    )
    assert response.status_code == 200
    assert federated_event.title in response.text

    response = response.form.submit(name="signup_choice", value="sign_up").follow()
    assert response.status_code == 200
    assert FederatedParticipation.objects.count() == 1
    assert federated_user.display_name in response.text


def test_federation_add_included_qualifications(django_app, federation, qualifications):
    host, guest = federation
    view = FederationOAuthView()
    view.guest = guest
    view._create_user({
        "email": "test@localhost",
        "display_name": "Test",
        "date_of_birth": "2000-01-01",
        "qualifications": [
            {
                "uuid": "123aaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "includes": [qualifications.rs.uuid],
            }
        ],
    })
    user = FederatedUser.objects.get(email="test@localhost")
    assert set(user.qualifications.all()) == {qualifications.rs}
