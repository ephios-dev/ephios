from django.urls import reverse
from guardian.shortcuts import remove_perm

from ephios.core.models import AbstractParticipation, LocalParticipation


def test_participation_list_permissions(django_app, event, planner, groups, volunteer, manager):
    LocalParticipation.objects.create(
        user=volunteer, shift=event.shifts.first(), state=AbstractParticipation.States.CONFIRMED
    )
    response = django_app.get(
        reverse("api:user-participations-list", kwargs=dict(user=volunteer.pk)),
        user=planner,
        status=200,
    )
    assert event.title in response

    # make event invisible to volunteers
    _, planners, volunteers = groups
    remove_perm("view_event", planners, event)
    remove_perm("view_event", volunteers, event)
    remove_perm("view_event", planner, event)

    response = django_app.get(
        reverse("api:user-participations-list", kwargs=dict(user=volunteer.pk)),
        user=planner,
        status=200,
    )
    assert event.title not in response
    assert event.title in django_app.get(
        reverse("api:user-participations-list", kwargs=dict(user=volunteer.pk)),
        user=manager,
        status=200,
    )


def test_participation_list_filter(
    django_app, event, planner, groups, volunteer, manager, training_event_type
):
    LocalParticipation.objects.create(
        user=volunteer, shift=event.shifts.first(), state=AbstractParticipation.States.CONFIRMED
    )
    response = django_app.get(
        reverse("api:user-participations-list", kwargs=dict(user=volunteer.pk)),
        user=planner,
        status=200,
    )
    assert event.title in response

    response = django_app.get(
        f"{reverse('api:user-participations-list', kwargs=dict(user=volunteer.pk))}?shift__event__type={training_event_type.pk}",
        user=planner,
        status=200,
    )
    assert event.title not in response
