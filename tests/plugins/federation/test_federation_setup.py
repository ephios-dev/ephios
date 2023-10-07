import base64
import json

from django.urls import reverse
from dynamic_preferences.registries import global_preferences_registry

from ephios.plugins.federation.models import FederatedGuest, FederatedHost, InviteCode


def test_create_invitecode(django_app, superuser):
    form = django_app.get(reverse("federation:create_invite_code"), user=superuser).form
    form["url"] = "https://example.com"
    form.submit().follow()
    assert InviteCode.objects.get().url == "https://example.com"


def test_redeem_invitecode_frontend(
    django_app, superuser, invite_code, live_server, django_db_serialized_rollback
):
    global_preferences_registry.manager()["general__organization_name"] = "Test"
    form = django_app.get(reverse("federation:frontend_redeem_invite_code"), user=superuser).form
    form["code"] = base64.b64encode(
        json.dumps(
            {"guest_url": invite_code.url, "code": invite_code.code, "host_url": live_server.url}
        ).encode("ascii")
    ).decode("ascii")
    response = form.submit().follow()
    assert FederatedGuest.objects.count() == 1
    assert FederatedHost.objects.count() == 1


def test_redeem_invitecode_api(django_app, superuser, invite_code):
    response = django_app.post_json(
        reverse("federation:redeem_invite_code"),
        {
            "code": invite_code.code,
            "url": "http://localhost:8000",
            "name": "Test",
            "client_id": "test",
            "client_secret": "test",
        },
        user=superuser,
    )
    assert response.json["url"] == invite_code.url
    assert FederatedGuest.objects.count() == 1
