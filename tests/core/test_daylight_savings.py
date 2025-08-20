from datetime import datetime

import pytest
from django.urls import reverse

from ephios.plugins.baseshiftstructures.structure.uniform import UniformShiftStructure
from ephios.plugins.basesignupflows.flow.participant import InstantConfirmSignupFlow


@pytest.fixture
def end_in_rollback_shift(event, tz):
    # this shift cannot be configured using the shift form,
    # because we don't allow ambiguous datetimes in the form
    assert "Berlin" in tz.key
    return event.shifts.create(
        start_time=datetime(2026, 10, 24, 20, 0, tzinfo=tz),
        end_time=datetime(2026, 10, 25, 2, 30, tzinfo=tz),
        meeting_time=datetime(2026, 10, 24, 19, 0).astimezone(tz),
        signup_flow_slug=InstantConfirmSignupFlow.slug,
        structure_slug=UniformShiftStructure.slug,
    )


def test_signup_into_clock_rollback(django_app, volunteer, end_in_rollback_shift):
    response = django_app.get(
        volunteer.as_participant().reverse_signup_action(end_in_rollback_shift),
        user=volunteer,
    ).form.submit()
    # not using quick signup, but the customization view, signup might fail with indvalid individual time fields
    # if their field values are ambigous (which can exist e.g. when copying shifts around)
    assert "may be ambiguous" in response.text


def test_cannot_configure_ambiguous_shift_end_time(django_app, planner, end_in_rollback_shift):
    response = django_app.get(
        reverse("core:shift_edit", kwargs={"pk": end_in_rollback_shift.pk}),
        user=planner,
    ).form.submit()
    assert "may be ambiguous" in response.text
