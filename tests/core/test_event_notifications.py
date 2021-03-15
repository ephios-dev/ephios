import pytest
from django.urls import reverse
from guardian.shortcuts import get_users_with_perms

from ephios.core.forms.events import EventNotificationForm
from ephios.core.models import AbstractParticipation, LocalParticipation, Notification, UserProfile


@pytest.mark.django_db
class TestEventNotifications:
    def test_mail_new_event(self, django_app, event, volunteer, planner, groups):
        form = django_app.get(
            reverse("core:event_notifications", kwargs=dict(pk=event.id)), user=planner
        ).form
        form["action"] = EventNotificationForm.NEW_EVENT
        response = form.submit()
        assert response.status_code == 302
        assert (
            Notification.objects.count()
            == get_users_with_perms(event, only_with_perms_in=["view_event"]).count()
        )

    def test_mail_reminder(self, django_app, event, volunteer, planner, groups):
        form = django_app.get(
            reverse("core:event_notifications", kwargs=dict(pk=event.id)), user=planner
        ).form
        form["action"] = EventNotificationForm.REMINDER
        response = form.submit()
        assert response.status_code == 302
        users_not_participating = UserProfile.objects.exclude(
            pk__in=AbstractParticipation.objects.filter(shift__event=event).values_list(
                "localparticipation__user", flat=True
            )
        )
        assert Notification.objects.count() == users_not_participating.count()

    def test_mail_participants(self, django_app, event, volunteer, planner, groups):
        LocalParticipation.objects.create(
            shift=event.shifts.first(),
            user=volunteer,
            state=AbstractParticipation.States.CONFIRMED,
        )
        form = django_app.get(
            reverse("core:event_notifications", kwargs=dict(pk=event.id)), user=planner
        ).form
        form["action"] = EventNotificationForm.PARTICIPANTS
        form["mail_content"] = "hey there"
        response = form.submit()
        assert response.status_code == 302
        assert Notification.objects.count() == 1

    def test_mail_participants_content_required(
        self, django_app, event, volunteer, planner, groups
    ):
        form = django_app.get(
            reverse("core:event_notifications", kwargs=dict(pk=event.id)), user=planner
        ).form
        form["action"] = EventNotificationForm.PARTICIPANTS
        response = form.submit()
        assert response.status_code == 200
        assert Notification.objects.count() == 0
