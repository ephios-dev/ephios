import pytest
from django.urls import reverse
from dynamic_preferences.registries import global_preferences_registry

from ephios.plugins.guests.models import EventGuestShare, GuestParticipation, GuestUser


def test_guest_signup_flow(django_app, event, qualifications, volunteer):
    preferences = global_preferences_registry.manager()
    preferences["general__enabled_plugins"] = [
        "ephios.plugins.baseshiftstructures",
        "ephios.plugins.guests",
    ]

    # permission denied before share exists
    django_app.get(
        reverse(
            "guests:register", kwargs=dict(event_id=event.id, public_signup_token="somesecret")
        ),
        status=403,
    )

    share = EventGuestShare.objects.create(event=event, active=True)

    # permission denied with wrong secret
    django_app.get(
        reverse(
            "guests:register", kwargs=dict(event_id=event.id, public_signup_token="somesecret")
        ),
        status=403,
    )

    response = django_app.get(share.url, status=200)
    response.form["display_name"] = "Carlson Carlsen"
    response.form["email"] = "guest@localhost"
    response.form["date_of_birth"] = "2000-01-01"
    response.form["qualifications"] = [qualifications.nfs.id]
    assert not GuestUser.objects.exists()
    response = response.form.submit().follow()
    assert GuestUser.objects.exists()
    assert not GuestParticipation.objects.exists()
    response.form.submit(name="signup_choice", value="sign_up").follow()
    assert GuestParticipation.objects.get(shift=event.shifts.first())

    participant = GuestUser.objects.get().as_participant()
    django_app.get(participant.reverse_event_detail(event), status=200)
    preferences["general__enabled_plugins"] = ["ephios.plugins.baseshiftstructures"]
    django_app.get(participant.reverse_event_detail(event), status=403)


def test_guest_settings_flow(django_app, event, planner):
    preferences = global_preferences_registry.manager()
    preferences["general__enabled_plugins"] = ["ephios.plugins.baseshiftstructures"]

    event_update_view = django_app.get(
        reverse("core:event_edit", kwargs=dict(pk=event.pk)), user=planner
    )
    assert "Guests" not in event_update_view

    with pytest.raises(EventGuestShare.DoesNotExist):
        event.guest_share

    preferences["general__enabled_plugins"] = [
        "ephios.plugins.baseshiftstructures",
        "ephios.plugins.guests",
    ]
    event_update_view = django_app.get(
        reverse("core:event_edit", kwargs=dict(pk=event.pk)), user=planner
    )
    assert "Guests" in event_update_view
    assert not event_update_view.form["guests-active"].value
    event_update_view.form["guests-active"] = True
    event_update_view.form.submit()

    event.refresh_from_db()
    assert event.guest_share.active
    old_token = event.guest_share.token

    event_update_view = django_app.get(
        reverse("core:event_edit", kwargs=dict(pk=event.pk)), user=planner
    )
    event_update_view.form["guests-active"] = False
    event_update_view.form["guests-new_link"] = True
    event_update_view.form.submit()

    event.guest_share.refresh_from_db()
    assert event.guest_share.token != old_token
    assert not event.guest_share.active


def test_redirect_for_logged_in_users(django_app, event, volunteer):
    share = EventGuestShare.objects.create(event=event, active=True)
    assert (
        "Log out to register as guest"
        in django_app.get(
            share.url,
            user=volunteer,
        ).follow()
    )
