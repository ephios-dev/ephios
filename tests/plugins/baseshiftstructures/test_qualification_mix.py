from datetime import datetime

import pytest
from django.urls import reverse

from ephios.core.models import AbstractParticipation, LocalParticipation, Shift
from ephios.plugins.baseshiftstructures.structure.qualification_mix import (
    QualificationMixShiftStructure,
)
from ephios.plugins.basesignupflows.flow.participant import RequestConfirmSignupFlow


@pytest.fixture
def mixed_shift(event, tz, qualifications):
    return Shift.objects.create(
        event=event,
        meeting_time=datetime(2099, 7, 1, 7, 0).astimezone(tz),
        start_time=datetime(2099, 7, 1, 8, 0).astimezone(tz),
        end_time=datetime(2099, 7, 1, 20, 0).astimezone(tz),
        signup_flow_slug=RequestConfirmSignupFlow.slug,
        signup_flow_configuration={},
        structure_slug=QualificationMixShiftStructure.slug,
        structure_configuration={
            "minimum_age": None,
            "signup_until": None,
            "user_can_decline_confirmed": False,
            "choose_preferred_team": True,
            "qualification_requirements": [
                {
                    "qualification": qualifications.rs.id,
                    "min_count": 1,
                    "max_count": 1,
                },
                {
                    "qualification": qualifications.nfs.id,
                    "min_count": 1,
                    "max_count": 1,
                },
            ],
        },
    )


def test_signup_flow(django_app, qualified_volunteer, planner, event, mixed_shift):
    # signup for second shift
    django_app.get(
        event.get_absolute_url(),
        user=qualified_volunteer,
    ).forms[1].submit(name="signup_choice", value="sign_up").follow()
    assert (
        LocalParticipation.objects.get(user=qualified_volunteer, shift=mixed_shift).state
        == AbstractParticipation.States.REQUESTED
    )

    # confirm the participation as planner
    response = django_app.get(
        reverse("core:shift_disposition", kwargs=dict(pk=mixed_shift.pk)),
        user=planner,
    )
    form = response.forms["participations-form"]
    form["participations-0-state"] = AbstractParticipation.States.CONFIRMED.value
    form.submit()
    participation = LocalParticipation.objects.get(user=qualified_volunteer, shift=mixed_shift)
    assert participation.state == AbstractParticipation.States.CONFIRMED

    response = django_app.get(
        event.get_absolute_url(),
        user=qualified_volunteer,
    )


def test_signup_stats(mixed_shift, qualified_volunteer, planner):
    signup_stats = mixed_shift.get_signup_stats()
    assert signup_stats.missing == 2
    assert signup_stats.free == 2

    participation = LocalParticipation.objects.create(
        shift=mixed_shift,
        user=planner,
        state=AbstractParticipation.States.REQUESTED,
        structure_data={},
    )
    signup_stats = mixed_shift.get_signup_stats()
    assert signup_stats.min_count == signup_stats.missing == 2
    assert signup_stats.max_count == signup_stats.free == 2
    assert signup_stats.requested_count == 1
    assert signup_stats.confirmed_count == 0

    participation.state = AbstractParticipation.States.CONFIRMED
    participation.save()
    signup_stats = mixed_shift.get_signup_stats()
    assert signup_stats.min_count == signup_stats.missing == 2
    assert signup_stats.max_count == signup_stats.free == 2
    assert signup_stats.requested_count == 0
    assert signup_stats.confirmed_count == 1

    participation.user = qualified_volunteer
    participation.save()
    signup_stats = mixed_shift.get_signup_stats()
    assert signup_stats.max_count == signup_stats.min_count == 2
    assert signup_stats.free == signup_stats.missing == 1
    assert signup_stats.requested_count == 0
    assert signup_stats.confirmed_count == 1


def test_mixed_pdf(django_app, planner, mixed_shift, qualified_volunteer):
    response_no_participations = django_app.get(
        reverse("core:event_detail_pdf", kwargs=dict(pk=mixed_shift.event.pk)),
        user=planner,
    )
    assert response_no_participations
    LocalParticipation.objects.create(
        shift=mixed_shift,
        user=qualified_volunteer,
        state=AbstractParticipation.States.CONFIRMED,
        structure_data={},
    )
    response = django_app.get(
        reverse("core:event_detail_pdf", kwargs=dict(pk=mixed_shift.event.pk)),
        user=planner,
    )
    assert response and response != response_no_participations
