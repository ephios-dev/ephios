from importlib import import_module
from unittest.mock import patch

from django.urls import reverse

from ephios.plugins.federation.models import FederatedEventShare
from ephios.plugins.federation.serializers import SharedEventSerializer


def test_federation_get_shared_events(django_app, volunteer, federation, event):
    host, guest = federation
    share = FederatedEventShare.objects.create(event=event)
    share.shared_with.add(guest)

    response = django_app.get(
        reverse("federation:shared_event_list_view"),
        headers={"Authorization": f"Bearer {host.access_token}"},
    )
    assert event.title in response.text


@patch("ephios.plugins.federation.views.frontend.requests")
def test_federation_shared_event_list(
    mock_requests, django_app, volunteer, federation, event, settings
):
    host, guest = federation
    share = FederatedEventShare.objects.create(event=event)
    share.shared_with.add(guest)

    mock_requests.get.return_value.json.return_value = {
        "results": [SharedEventSerializer(event).data]
    }

    response = django_app.get(reverse("federation:external_event_list"), user=volunteer)
    assert response.status_code == 200
    assert event.title in response.text


def test_federation_shared_event_detail(
    django_app, volunteer, federation, federated_user, event, settings
):
    host, guest = federation
    session = django_app.session or import_module(settings.SESSION_ENGINE).SessionStore()
    session["federation_access_token"] = "token"
    session["federation_guest_pk"] = guest.pk
    session["federated_user"] = federated_user.pk
    session.save()
    django_app.set_cookie(settings.SESSION_COOKIE_NAME, session.session_key)
    share = FederatedEventShare.objects.create(event=event)
    share.shared_with.add(guest)

    response = django_app.get(reverse("federation:event_detail", kwargs={"pk": event.pk}))
    assert response.status_code == 200
    assert event.title in response.text
