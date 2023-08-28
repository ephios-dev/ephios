from django.core import mail
from django.core.management import call_command
from django.urls import reverse
from guardian.shortcuts import get_users_with_perms

from ephios.core.models import AbstractParticipation, LocalParticipation, Notification
from ephios.core.services.notifications.backends import enabled_notification_backends
from ephios.core.services.notifications.types import (
    ConsequenceApprovedNotification,
    ConsequenceDeniedNotification,
    CustomEventParticipantNotification,
    EventReminderNotification,
    NewEventNotification,
    NewProfileNotification,
    ParticipationConfirmedNotification,
    ParticipationCustomizationNotification,
    ParticipationRejectedNotification,
    ProfileUpdateNotification,
    ResponsibleConfirmedParticipationCustomizedNotification,
    ResponsibleParticipationRequestedNotification,
    enabled_notification_types,
)


class TestNotifications:
    def _enable_all_notifications(self, user):
        preferences = {}
        backends = [backend.slug for backend in enabled_notification_backends()]
        for notification_type in enabled_notification_types():
            if notification_type.unsubscribe_allowed:
                preferences[notification_type.slug] = backends
        user.preferences["notifications__notifications"] = preferences

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
        self._enable_all_notifications(volunteer)
        call_command("send_notifications")
        assert Notification.objects.count() == 0

    def test_event_notification_sending(self, event, volunteer):
        self._enable_all_notifications(volunteer)
        NewEventNotification.send(event)
        EventReminderNotification.send(event)
        assert Notification.objects.count() == 2 * len(
            get_users_with_perms(event, only_with_perms_in=["core.view_event"])
        )
        call_command("send_notifications")
        assert Notification.objects.count() == 0

    def test_participation_notification_sending(self, event, qualified_volunteer):
        self._enable_all_notifications(qualified_volunteer)
        participation = LocalParticipation.objects.create(
            shift=event.shifts.first(),
            user=qualified_volunteer,
            state=AbstractParticipation.States.CONFIRMED,
        )
        ParticipationConfirmedNotification.send(participation)
        ParticipationRejectedNotification.send(participation)
        ResponsibleParticipationRequestedNotification.send(participation)
        assert Notification.objects.count() == 2 + len(
            get_users_with_perms(event, only_with_perms_in=["core.change_event"])
        )
        call_command("send_notifications")
        assert Notification.objects.count() == 0

    def test_responsible_confirmed_participation_customized_notification(
        self, django_app, event, planner, qualified_volunteer
    ):
        self._enable_all_notifications(planner)
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
        assert Notification.objects.count() == 0

    def test_participant_participation_customized_notification(
        self, django_app, event, planner, qualified_volunteer
    ):
        self._enable_all_notifications(qualified_volunteer)
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
        assert Notification.objects.count() == 0

    def test_inactive_user(self, volunteer):
        self._enable_all_notifications(volunteer)
        volunteer.is_active = False
        volunteer.save()
        ProfileUpdateNotification.send(volunteer)
        assert Notification.objects.count() == 1
        call_command("send_notifications")
        assert len(mail.outbox) == 0

    def test_consequence_notifications(self, volunteer, workinghours_consequence):
        self._enable_all_notifications(volunteer)
        ConsequenceApprovedNotification.send(workinghours_consequence)
        ConsequenceDeniedNotification.send(workinghours_consequence)
        assert Notification.objects.count() == 2
        call_command("send_notifications")
        assert Notification.objects.count() == 0

    def test_responsibles_receive_custom_notification(
        self, django_app, qualified_volunteer, planner, event
    ):
        self._enable_all_notifications(qualified_volunteer)
        participation = LocalParticipation.objects.create(
            shift=event.shifts.first(),
            user=qualified_volunteer,
            state=AbstractParticipation.States.CONFIRMED,
        )
        CustomEventParticipantNotification.send(event, "test notification")
        assert planner.has_perm("change_event", event)
        assert Notification.objects.get(user=planner)
