import pytest
from django.core import mail
from django.core.management import call_command
from django.urls import reverse
from guardian.shortcuts import get_users_with_perms

from ephios.core.models import AbstractParticipation, LocalParticipation, Notification
from ephios.core.services.notifications.backends import EmailNotificationBackend
from ephios.core.services.notifications.types import (
    NOTIFICATION_READ_PARAM_NAME,
    ConsequenceApprovedNotification,
    ConsequenceDeniedNotification,
    NewProfileNotification,
    ParticipationCustomizationNotification,
    ParticipationStateChangeNotification,
    ProfileUpdateNotification,
    ResponsibleConfirmedParticipationCustomizedNotification,
    ResponsibleParticipationAwaitsDispositionNotification,
    enabled_notification_types,
)


def test_notification_form_render(django_app, volunteer):
    form = django_app.get(reverse("core:settings_notifications"), user=volunteer).form
    types = filter(
        lambda notification_type: notification_type.unsubscribe_allowed,
        enabled_notification_types(),
    )
    assert all(notification_type.slug in form.fields.keys() for notification_type in types)


def test_notification_form_submit(django_app, volunteer):
    form = django_app.get(reverse("core:settings_notifications"), user=volunteer).form
    form["ephios_participation_awaits_disposition"] = ["ephios_backend_email"]
    form.submit()
    assert (
        "ephios_backend_email"
        in volunteer.preferences["notifications__notifications"][
            "ephios_participation_awaits_disposition"
        ]
    )


def test_user_notification_sending(volunteer):
    NewProfileNotification.send(volunteer)
    ProfileUpdateNotification.send(volunteer)
    assert Notification.objects.count() == 2
    call_command("send_notifications")
    assert not Notification.objects.filter(processing_completed=False).exists()


def test_participation_notification_sending(event, qualified_volunteer):
    participation = LocalParticipation.objects.create(
        shift=event.shifts.first(),
        user=qualified_volunteer,
        state=AbstractParticipation.States.CONFIRMED,
    )
    ParticipationStateChangeNotification.send(participation)
    ResponsibleParticipationAwaitsDispositionNotification.send(participation)
    assert Notification.objects.count() == 1 + len(
        get_users_with_perms(event, only_with_perms_in=["change_event"])
    )
    call_command("send_notifications")
    assert not Notification.objects.filter(processing_completed=False).exists()


def test_responsible_confirmed_participation_customized_notification(
    django_app, event, planner, qualified_volunteer
):
    participation = LocalParticipation.objects.create(
        shift=event.shifts.first(),
        user=qualified_volunteer,
        state=AbstractParticipation.States.CONFIRMED,
    )
    # change individual start time
    form = django_app.get(
        reverse("core:signup_action", kwargs=dict(pk=participation.shift.pk)),
        user=qualified_volunteer,
    ).form
    form["individual_start_time_1"] = "07:42"
    form.submit(name="signup_choice", value="customize").follow()

    # assert only notification of the correct type exist
    assert set(Notification.objects.all().values_list("slug", flat=True)) == {
        ResponsibleConfirmedParticipationCustomizedNotification.slug
    }
    plaintext = ResponsibleConfirmedParticipationCustomizedNotification.get_body(
        Notification.objects.first()
    )
    assert "7:42" in plaintext
    call_command("send_notifications")
    assert not Notification.objects.filter(processing_completed=False).exists()


def test_participant_participation_customized_notification(
    django_app, event, planner, qualified_volunteer
):
    participation = LocalParticipation.objects.create(
        shift=event.shifts.first(),
        user=qualified_volunteer,
        state=AbstractParticipation.States.CONFIRMED,
    )
    # change individual start time
    response = django_app.get(
        reverse("core:shift_disposition", kwargs=dict(pk=participation.shift.pk)),
        user=planner,
    )
    form = response.forms["participations-form"]
    form["participations-0-individual_start_time_1"] = "07:42"
    form.submit()

    # assert only notification of the correct type exist
    assert Notification.objects.get().slug == ParticipationCustomizationNotification.slug

    plaintext = ParticipationCustomizationNotification.get_body(Notification.objects.first())
    assert "7:42" in plaintext
    call_command("send_notifications")
    assert not Notification.objects.filter(processing_completed=False).exists()


def test_responsibles_dont_get_notified_about_own_disposition_action(
    django_app, event, planner, qualified_volunteer
):
    participation = LocalParticipation.objects.create(
        shift=event.shifts.first(),
        user=qualified_volunteer,
        state=AbstractParticipation.States.REQUESTED,
    )
    # change individual start time
    response = django_app.get(
        reverse("core:shift_disposition", kwargs=dict(pk=participation.shift.pk)),
        user=planner,
    )
    form = response.forms["participations-form"]
    form["participations-0-state"] = AbstractParticipation.States.CONFIRMED
    form.submit()

    # the planner that did the disposition should not be notified about their own action
    call_command("send_notifications")
    for m in mail.outbox:
        assert "Luisa Durchblick <luisa@localhost>" not in m.to


def test_responsibles_dont_get_notified_about_own_signup(django_app, event, planner):
    django_app.get(
        event.get_absolute_url(),
        user=planner,
    ).form.submit(name="signup_choice", value="sign_up").follow()
    # even if responsible, the planner that signed themselves up should not be notified about their own action
    call_command("send_notifications")
    for m in mail.outbox:
        assert "Luisa Durchblick <luisa@localhost>" not in m.to


def test_inactive_user(volunteer):
    volunteer.is_active = False
    volunteer.save()
    ProfileUpdateNotification.send(volunteer)
    assert Notification.objects.count() == 1
    call_command("send_notifications")
    assert len(mail.outbox) == 0


def test_consequence_notifications(volunteer, workinghours_consequence):
    ConsequenceApprovedNotification.send(workinghours_consequence)
    ConsequenceDeniedNotification.send(workinghours_consequence)
    assert Notification.objects.count() == 2
    call_command("send_notifications")
    assert not Notification.objects.filter(processing_completed=False).exists()


def test_middleware_marks_notification_as_read(django_app, qualified_volunteer, planner, event):
    participation = LocalParticipation.objects.create(
        shift=event.shifts.first(),
        user=qualified_volunteer,
        state=AbstractParticipation.States.CONFIRMED,
    )
    ResponsibleParticipationAwaitsDispositionNotification.send(participation)
    notification = Notification.objects.get(
        user=planner, slug=ResponsibleParticipationAwaitsDispositionNotification.slug
    )
    assert not notification.read
    django_app.get(notification.get_actions()[0][1], user=planner)
    notification.refresh_from_db()
    assert notification.read


def test_broken_middleware_query_param(django_app, planner):
    django_app.get(
        f"/?{NOTIFICATION_READ_PARAM_NAME}=1",
        user=None,  # anonymous user
    )
    django_app.get(
        f"/?{NOTIFICATION_READ_PARAM_NAME}",
        user=planner,
    )
    django_app.get(
        f"/?{NOTIFICATION_READ_PARAM_NAME}=123",
        user=planner,
    )
    django_app.get(
        f"/?{NOTIFICATION_READ_PARAM_NAME}=abc",
        user=planner,
    )
    django_app.get(
        f"/?{NOTIFICATION_READ_PARAM_NAME}=1&{NOTIFICATION_READ_PARAM_NAME}=2",
        user=planner,
    )


def test_notification_doesnotexist_gets_deleted(django_app, qualified_volunteer, event):
    participation = LocalParticipation.objects.create(
        shift=event.shifts.first(),
        user=qualified_volunteer,
        state=AbstractParticipation.States.CONFIRMED,
    )
    ParticipationStateChangeNotification.send(participation)
    notification = Notification.objects.get(
        user=qualified_volunteer, slug=ParticipationStateChangeNotification.slug
    )
    participation.delete()
    EmailNotificationBackend.send_multiple([notification])
    with pytest.raises(Notification.DoesNotExist):
        notification.refresh_from_db()
