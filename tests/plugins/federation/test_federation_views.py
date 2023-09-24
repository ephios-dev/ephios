from django.urls import reverse

from ephios.plugins.federation.models import FederatedEventShare


def test_federation_get_shared_events(
    django_app, volunteer, live_server, django_db_serialized_rollback, federation, event
):
    host, guest = federation(live_server.url)
    share = FederatedEventShare.objects.create(event=event)
    share.shared_with.add(guest)

    response = django_app.get(
        reverse("federation:shared_event_list_view"),
        headers={"Authorization": f"Bearer {host.access_token}"},
    )
    assert event.title in response.text
