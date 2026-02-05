from collections import OrderedDict
from datetime import datetime

import pytest
from django.urls import reverse

from ephios.core.models import AbstractParticipation, LocalParticipation, Shift
from ephios.plugins.baseshiftstructures.structure.named_teams import NamedTeamsShiftStructure
from ephios.plugins.basesignupflows.flow.participant import RequestConfirmSignupFlow

KTW_UUID = "f92fe836-6dc5-4afd-b488-aee3fe7eda32"


@pytest.fixture
def teamed_shift(event, tz, qualifications):
    return Shift.objects.create(
        event=event,
        meeting_time=datetime(2099, 7, 1, 7, 0).astimezone(tz),
        start_time=datetime(2099, 7, 1, 8, 0).astimezone(tz),
        end_time=datetime(2099, 7, 1, 20, 0).astimezone(tz),
        signup_flow_slug=RequestConfirmSignupFlow.slug,
        signup_flow_configuration={},
        structure_slug=NamedTeamsShiftStructure.slug,
        structure_configuration={
            "minimum_age": None,
            "signup_until": None,
            "user_can_decline_confirmed": False,
            "choose_preferred_team": True,
            "teams": [
                {
                    "title": "KTW",
                    "qualification": qualifications.rs,
                    "min_count": 2,
                    "uuid": KTW_UUID,
                },
                {
                    "title": "ITS",
                    "qualification": qualifications.na,
                    "min_count": 1,
                    "uuid": "e2df480f-1f11-442c-be11-3cccf7e6ea19",
                },
            ],
        },
    )


@pytest.mark.ignore_template_errors  # shift_form uses unbound object to detect shift creation
def test_configuration(csrf_exempt_django_app, planner, event, qualifications):
    POST_DATA = OrderedDict({
        "choose_preferred_team": "on",
        "date": "2023-06-30",
        "end_time": "01:00:00",
        "meeting_time": "15:30:00",
        "minimum_age": "",
        "teams": "",
        "teams-0-min_count": "2",
        "teams-0-qualifications": str(qualifications.rs.id),
        "teams-0-title": "KTW 10-85-1",
        "teams-0-uuid": "",
        "teams-1-min_count": "2",
        "teams-1-qualifications": str(qualifications.na.id),
        "teams-1-title": "ITS",
        "teams-1-uuid": "",
        "teams-INITIAL_FORMS": "2",
        "teams-MAX_NUM_FORMS": "1000",
        "teams-MIN_NUM_FORMS": "1",
        "teams-TOTAL_FORMS": "2",
        "signup_flow_slug": RequestConfirmSignupFlow.slug,
        "structure_slug": NamedTeamsShiftStructure.slug,
        "signup_until_0": "",
        "signup_until_1": "",
        "start_time": "16:00:00",
    })

    csrf_exempt_django_app.get(
        reverse("core:event_createshift", kwargs=dict(pk=event.pk)),
        user=planner,
    )
    # no csrf check for plain post
    csrf_exempt_django_app.post(
        reverse("core:event_createshift", kwargs=dict(pk=event.pk)),
        user=planner,
        params=POST_DATA,
    ).follow()
    _, shift = event.shifts.order_by("id")
    assert shift.structure_slug == NamedTeamsShiftStructure.slug
    assert len(shift.structure.configuration.teams) == 2


def test_signup_flow(django_app, qualified_volunteer, planner, event, teamed_shift):
    # request a participation as volunteer on *second* shift
    response = (
        django_app
        .get(
            event.get_absolute_url(),
            user=qualified_volunteer,
        )
        .forms[1]
        .submit(name="signup_choice", value="sign_up")
        .follow()
    )
    response.form["baseshiftstructures_named_teams_preferred_team_uuid"] = KTW_UUID
    response.form.submit(name="signup_choice", value="sign_up").follow()
    assert (
        LocalParticipation.objects.get(user=qualified_volunteer, shift=teamed_shift).state
        == AbstractParticipation.States.REQUESTED
    )

    # confirm the participation as planner
    response = django_app.get(
        reverse("core:shift_disposition", kwargs=dict(pk=teamed_shift.pk)),
        user=planner,
    )
    form = response.forms["participations-form"]
    form["participations-0-state"] = AbstractParticipation.States.CONFIRMED.value
    form.submit()
    participation = LocalParticipation.objects.get(user=qualified_volunteer, shift=teamed_shift)
    assert participation.state == AbstractParticipation.States.CONFIRMED
    assert participation.structure_data.get("preferred_team_uuid") == KTW_UUID
    assert participation.structure_data.get("dispatched_team_uuid") == KTW_UUID


def test_signup_stats(django_app, teamed_shift, volunteer, planner):
    signup_stats = teamed_shift.get_signup_stats()
    assert signup_stats.missing == 3
    assert signup_stats.free is None
    teamed_shift.structure_configuration["teams"] = [
        {
            "title": "KTW",
            "qualification": None,
            "min_count": 2,
            "max_count": 3,
            "uuid": KTW_UUID,
        },
    ]
    teamed_shift.save()
    signup_stats = teamed_shift.get_signup_stats()
    assert signup_stats.min_count == signup_stats.missing == 2
    assert signup_stats.max_count == signup_stats.free == 3
    assert signup_stats.requested_count == signup_stats.confirmed_count == 0

    unassigned_participation = LocalParticipation.objects.create(
        shift=teamed_shift,
        user=planner,
        state=AbstractParticipation.States.REQUESTED,
        structure_data=dict(dispatched_team_uuid=None),
    )
    signup_stats = teamed_shift.get_signup_stats()
    assert signup_stats.min_count == signup_stats.missing == 2
    assert signup_stats.max_count == signup_stats.free == 3
    assert signup_stats.requested_count == 1
    assert signup_stats.confirmed_count == 0

    # a confirmed unassigned participation does not change the missing/max values
    unassigned_participation.state = AbstractParticipation.States.CONFIRMED
    unassigned_participation.save()
    signup_stats = teamed_shift.get_signup_stats()
    assert signup_stats.min_count == signup_stats.missing == 2
    assert signup_stats.max_count == signup_stats.free == 3
    assert signup_stats.requested_count == 0
    assert signup_stats.confirmed_count == 1

    LocalParticipation.objects.create(
        shift=teamed_shift,
        user=volunteer,
        state=AbstractParticipation.States.CONFIRMED,
        structure_data=dict(dispatched_team_uuid=KTW_UUID),
    )

    assert django_app.get(
        reverse(
            "core:event_detail",
            kwargs=dict(
                pk=teamed_shift.event.pk,
                slug="nottheactualslug",
            ),
        ),
        user=planner,
    ).follow()

    signup_stats = teamed_shift.get_signup_stats()
    assert signup_stats.min_count == 2
    assert signup_stats.missing == 1
    assert signup_stats.max_count == 3
    assert signup_stats.free == 2
    assert signup_stats.requested_count == 0
    assert signup_stats.confirmed_count == 2


def test_team_based_pdf(django_app, planner, teamed_shift, volunteer):
    response_no_participations = django_app.get(
        reverse("core:event_detail_pdf", kwargs=dict(pk=teamed_shift.event.pk)),
        user=planner,
    )
    assert response_no_participations
    LocalParticipation.objects.create(
        shift=teamed_shift,
        user=volunteer,
        state=AbstractParticipation.States.CONFIRMED,
        structure_data=dict(dispatched_team_uuid=KTW_UUID),
    )
    response = django_app.get(
        reverse("core:event_detail_pdf", kwargs=dict(pk=teamed_shift.event.pk)),
        user=planner,
    )
    assert response and response != response_no_participations
