from django.urls import reverse

from ephios.core.models import AbstractParticipation, EventType, LocalParticipation


def test_show_participation_data_filter(django_app, volunteer, event, planner):
    LocalParticipation.objects.create(
        user=planner, shift=event.shifts.first(), state=AbstractParticipation.States.CONFIRMED
    )
    assert (
        django_app.get(
            reverse("api:participations-list"),
            user=volunteer,
        ).json["count"]
        == 1
    )

    event.type.show_participant_data = EventType.ShowParticipantDataChoices.CONFIRMED
    event.type.save()
    assert (
        django_app.get(
            reverse("api:participations-list"),
            user=volunteer,
        ).json["count"]
        == 0
    )
    assert (
        django_app.get(
            reverse("api:participations-list"),
            user=planner,
        ).json["count"]
        == 1
    )

    event.type.show_participant_data = EventType.ShowParticipantDataChoices.RESPONSIBLES
    event.type.save()
    assert (
        django_app.get(
            reverse("api:participations-list"),
            user=volunteer,
        ).json["count"]
        == 0
    )
    assert (
        django_app.get(
            reverse("api:participations-list"),
            user=planner,
        ).json["count"]
        == 1
    )

    LocalParticipation.objects.create(
        user=volunteer, shift=event.shifts.first(), state=AbstractParticipation.States.CONFIRMED
    )
    assert (
        django_app.get(
            reverse("api:participations-list"),
            user=volunteer,
        ).json["count"]
        == 1
    )
    assert (
        django_app.get(
            reverse("api:participations-list"),
            user=planner,
        ).json["count"]
        == 2
    )

    event.type.show_participant_data = EventType.ShowParticipantDataChoices.CONFIRMED
    event.type.save()
    assert (
        django_app.get(
            reverse("api:participations-list"),
            user=volunteer,
        ).json["count"]
        == 2
    )
    assert (
        django_app.get(
            reverse("api:participations-list"),
            user=planner,
        ).json["count"]
        == 2
    )


def test_participation_permissions(django_app, volunteer, event, planner, manager, groups):
    LocalParticipation.objects.create(
        user=volunteer, shift=event.shifts.first(), state=AbstractParticipation.States.CONFIRMED
    )
    response = django_app.get(
        reverse("api:participations-list"),
        user=volunteer,
        status=200,
    )
    assert event.title in response
    django_app.get(
        reverse("api:userinfo-participations-list"),
        user=volunteer,
        status=403,
    )
    django_app.get(
        reverse("api:userinfo-participations-list"),
        user=volunteer,
        status=403,
    )
    django_app.get(
        reverse("api:userinfo-participations-list"),
        user=manager,
        status=200,
    )


def test_user_participation_list_permissions(
    django_app, event, planner, groups, volunteer, manager
):
    LocalParticipation.objects.create(
        user=volunteer, shift=event.shifts.first(), state=AbstractParticipation.States.CONFIRMED
    )
    response = django_app.get(
        reverse("api:user-participations-list", kwargs=dict(user=volunteer.pk)),
        user=manager,
        status=200,
    )
    assert event.title in response
    django_app.get(
        reverse("api:user-participations-list", kwargs=dict(user=volunteer.pk)),
        user=planner,
        status=403,
    )


def test_user_participation_list_filter(
    django_app, event, planner, groups, volunteer, manager, training_event_type
):
    LocalParticipation.objects.create(
        user=volunteer, shift=event.shifts.first(), state=AbstractParticipation.States.CONFIRMED
    )
    response = django_app.get(
        reverse("api:user-participations-list", kwargs=dict(user=volunteer.pk)),
        user=manager,
        status=200,
    )
    assert event.title in response

    response = django_app.get(
        f"{reverse('api:user-participations-list', kwargs=dict(user=volunteer.pk))}?event_type={training_event_type.pk}",
        user=manager,
        status=200,
    )
    assert event.title not in response
