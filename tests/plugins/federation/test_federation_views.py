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


def test_federation_shared_event_detail(
    django_app, volunteer, live_server, django_db_serialized_rollback, federation, event, settings
):
    settings.GET_SITE_URL = lambda: live_server.url
    host, guest = federation(live_server.url)
    share = FederatedEventShare.objects.create(event=event)
    share.shared_with.add(guest)

    event_url = reverse("federation:event_detail", kwargs={"pk": event.pk})
    response = django_app.get(f"{event_url}?referrer={live_server.url}", user=volunteer)
    response = response.follow()
    assert response.status_code == 200
    assert "Authorize" in response.text
    response = response.form.submit("allow").follow().follow()
    assert response.status_code == 200
    assert event.title in response.text
