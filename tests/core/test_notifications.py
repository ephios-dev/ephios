import pytest
from django.core import mail
from django.core.management import call_command
from django.urls import reverse
from guardian.shortcuts import get_users_with_perms

from ephios.core.models import AbstractParticipation, LocalParticipation, Notification
from ephios.core.services.notifications.backends import EmailNotificationBackend
from ephios.core.services.notifications.types import (
    ConsequenceApprovedNotification,
    ConsequenceDeniedNotification,
    CustomEventParticipantNotification,
    EventReminderNotification,
    NewEventNotification,
    NewProfileNotification,
    ParticipationCustomizationNotification,
    ParticipationStateChangeNotification,
    ProfileUpdateNotification,
    ResponsibleConfirmedParticipationCustomizedNotification,
    ResponsibleParticipationAwaitsDispositionNotification,
    enabled_notification_types,
)


class TestNotifications:
    def test_notification_form_render(self, django_app, volunteer):
        form = django_app.get(reverse("core:settings_notifications"), user=volunteer).form
        types = filter(
            lambda notification_type: notification_type.unsubscribe_allowed,
            enabled_notification_types(),
        )
        assert all(notification_type.slug in form.fields.keys() for notification_type in types)

    def test_notification_form_submit(self, django_app, volunteer):
        form = django_app.get(reverse("core:settings_notifications"), user=volunteer).form
        form["ephios_new_event"] = ["ephios_backend_email"]
        form.submit()
        assert (
            "ephios_backend_email"
            in volunteer.preferences["notifications__notifications"]["ephios_new_event"]
        )

    def test_user_notification_sending(self, volunteer):
        NewProfileNotification.send(volunteer)
        ProfileUpdateNotification.send(volunteer)
        assert Notification.objects.count() == 2
        call_command("send_notifications")
        assert not Notification.objects.filter(processing_completed=False).exists()

    def test_event_notification_sending(self, event, volunteer):
        NewEventNotification.send(event)
        EventReminderNotification.send(event)
        assert Notification.objects.count() == 2 * len(
            get_users_with_perms(event, only_with_perms_in=["view_event"])
        )
        call_command("send_notifications")
        assert not Notification.objects.filter(processing_completed=False).exists()

    def test_participation_notification_sending(self, event, qualified_volunteer):
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
        self, django_app, event, planner, qualified_volunteer
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
        self, django_app, event, planner, qualified_volunteer
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

    def test_inactive_user(self, volunteer):
        volunteer.is_active = False
        volunteer.save()
        ProfileUpdateNotification.send(volunteer)
        assert Notification.objects.count() == 1
        call_command("send_notifications")
        assert len(mail.outbox) == 0

    def test_consequence_notifications(self, volunteer, workinghours_consequence):
        ConsequenceApprovedNotification.send(workinghours_consequence)
        ConsequenceDeniedNotification.send(workinghours_consequence)
        assert Notification.objects.count() == 2
        call_command("send_notifications")
        assert not Notification.objects.filter(processing_completed=False).exists()

    def test_responsibles_receive_custom_notification(
        self, django_app, qualified_volunteer, planner, event
    ):
        participation = LocalParticipation.objects.create(
            shift=event.shifts.first(),
            user=qualified_volunteer,
            state=AbstractParticipation.States.CONFIRMED,
        )
        CustomEventParticipantNotification.send(event, "test notification")
        assert planner.has_perm("change_event", event)
        assert Notification.objects.get(user=planner)

    def test_middleware_marks_notification_as_read(
        self, django_app, qualified_volunteer, planner, event
    ):
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
        response = django_app.get(notification.get_actions()[0][1], user=planner)
        notification.refresh_from_db()
        assert notification.read

    def test_notification_doesnotexist_gets_deleted(self, django_app, qualified_volunteer, event):
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
