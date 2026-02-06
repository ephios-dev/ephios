from datetime import datetime

import pytest
from django.template.loader import get_template
from django.urls import reverse

from ephios.core.models import AbstractParticipation, LocalParticipation
from ephios.modellogging.models import LogEntry
from ephios.plugins.baseshiftstructures.structure.uniform import UniformShiftStructure
from ephios.plugins.basesignupflows.flow.coupled import CoupledSignupFlow
from ephios.plugins.basesignupflows.flow.participant import RequestConfirmSignupFlow


@pytest.fixture
def create_coupled_shift(event, tz):
    leader_shift = event.shifts.first()

    def factory():
        return event.shifts.create(
            meeting_time=datetime(2099, 7, 1, 7, 0).astimezone(tz),
            start_time=datetime(2099, 7, 1, 8, 0).astimezone(tz),
            end_time=datetime(2099, 7, 1, 20, 0).astimezone(tz),
            signup_flow_slug=CoupledSignupFlow.slug,
            structure_slug=leader_shift.structure_slug,
            structure_configuration=leader_shift.structure_configuration,
            signup_flow_configuration={"leader_shift_id": leader_shift.id},
        )

    return factory


def test_new_participation_gets_copied(django_app, volunteer, event, create_coupled_shift):
    coupled_shift = create_coupled_shift()
    response = django_app.get(event.get_absolute_url(), user=volunteer)
    response.forms[0].submit(name="signup_choice", value="sign_up")
    assert LocalParticipation.objects.filter(
        user=volunteer, shift=coupled_shift, state=AbstractParticipation.States.REQUESTED
    ).exists()


def test_new_shift_copies_participation(django_app, volunteer, event, create_coupled_shift):
    response = django_app.get(event.get_absolute_url(), user=volunteer)
    response.form.submit(name="signup_choice", value="sign_up")
    coupled_shift = create_coupled_shift()
    assert LocalParticipation.objects.filter(
        user=volunteer, shift=coupled_shift, state=AbstractParticipation.States.REQUESTED
    ).exists()


@pytest.mark.parametrize(
    "state,copy",
    [
        (state, state not in [AbstractParticipation.States.GETTING_DISPATCHED])
        for state in AbstractParticipation.States
    ],
)
def test_correct_states_get_copied(django_app, event, volunteer, create_coupled_shift, state, copy):
    coupled_shift = create_coupled_shift()
    LocalParticipation.objects.create(
        user=volunteer, shift=event.shifts.exclude(id=coupled_shift.id).get(), state=state
    )
    if copy:
        assert LocalParticipation.objects.filter(
            user=volunteer, shift=coupled_shift, state=state
        ).exists()
    else:
        assert not LocalParticipation.objects.filter(user=volunteer, shift=coupled_shift).exists()


def test_event_detail_with_missing_leader_shift(django_app, volunteer, event, create_coupled_shift):
    event.shifts.all().delete()
    create_coupled_shift()
    response = django_app.get(event.get_absolute_url(), user=volunteer)
    assert "leading shift is missing" in response


class Uniform:
    pass


def test_editing_coupled_shift_with_missing_leader_shift(
    django_app, planner, event, create_coupled_shift, tz
):
    coupled_shift = create_coupled_shift()
    response = django_app.get(
        reverse("core:shift_delete", kwargs={"pk": event.shifts.first().pk}), user=planner
    )
    response = response.form.submit().follow()
    assert "leading shift is missing" in response
    new_shift = event.shifts.create(
        meeting_time=datetime(2099, 7, 1, 7, 0).astimezone(tz),
        start_time=datetime(2099, 7, 1, 8, 0).astimezone(tz),
        end_time=datetime(2099, 7, 1, 20, 0).astimezone(tz),
        signup_flow_slug=RequestConfirmSignupFlow.slug,
        structure_slug=UniformShiftStructure.slug,
    )
    response = django_app.get(
        reverse("core:shift_edit", kwargs={"pk": coupled_shift.pk}), user=planner
    )
    response.form["leader_shift_id"] = new_shift.pk
    response.form.submit()
    log_message = get_template("modellogging/logentry.html").render({
        "log": LogEntry.objects.first()
    })
    assert "missing" in log_message
