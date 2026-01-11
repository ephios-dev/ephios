from django.urls import reverse

from ephios.core.models import AbstractParticipation, LocalParticipation, Notification
from ephios.core.models.events import PlaceholderParticipation


def test_mass_notification_not_without_perm(django_app, event, planner, volunteer):
    django_app.get(
        f"{reverse('core:notification_mass')}?event_id={event.pk}", user=volunteer, status=403
    )
    django_app.get(reverse("core:notification_mass"), user=planner, status=403)


def test_event_mass_notification(django_app, event, volunteer, planner):
    LocalParticipation.objects.create(
        shift=event.shifts.first(),
        user=volunteer,
        state=AbstractParticipation.States.CONFIRMED,
    )
    PlaceholderParticipation.objects.create(
        shift=event.shifts.first(),
        display_name="No-Email Participant",
        state=AbstractParticipation.States.CONFIRMED,
    )
    LocalParticipation.objects.create(
        shift=event.shifts.first(),
        user=planner,
        state=AbstractParticipation.States.REQUESTED,
    )
    response = django_app.get(event.get_absolute_url(), user=planner).click("Send notifications")
    form = response.form
    form["body"] = "Please remember to bring warm tea"
    form["to_participants"] = [volunteer.as_participant().identifier]
    form.submit().follow()
    assert Notification.objects.count() == 1


def test_mass_notification(django_app, groups, volunteer, manager):
    form = django_app.get(reverse("core:notification_mass"), user=manager).form
    form["subject"] = "A message from the manager"
    form["body"] = "Thank you for your support!"
    form["to_participants"] = [volunteer.as_participant().identifier]
    response = form.submit()
    response.follow()
    assert Notification.objects.count() == 1
