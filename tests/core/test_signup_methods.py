import functools
from datetime import datetime, timedelta

import pytest
from django.utils.timezone import make_aware

from ephios.core.models import AbstractParticipation, Shift
from ephios.core.signup import LocalParticipation, SignupStats, get_conflicting_participations
from ephios.plugins.basesignup.signup.instant import InstantConfirmationSignupMethod


def test_signup_stats_addition(django_app):
    a = SignupStats(4, 2, 3, None)
    b = SignupStats(5, 2, 3, 5)
    c = SignupStats(3, 2, None, 2)
    assert a + b == SignupStats(9, 4, 6, None)
    assert b + c == SignupStats(8, 4, 3, 7)


def test_cannot_sign_up_for_conflicting_shifts(django_app, volunteer, event, conflicting_event):
    assert not conflicting_event.shifts.first().signup_method.can_sign_up(
        volunteer.as_participant()
    )


@pytest.mark.parametrize(
    "a_times,b_times,conflict_expected",
    [
        (
            (datetime(2099, 1, 1, 8), datetime(2099, 1, 1, 12)),
            (datetime(2099, 1, 1, 6), datetime(2099, 1, 1, 8)),
            False,
        ),
        (
            (datetime(2099, 1, 1, 8), datetime(2099, 1, 1, 12)),
            (datetime(2099, 1, 1, 6), datetime(2099, 1, 1, 10)),
            True,
        ),
        (
            (datetime(2099, 1, 1, 8), datetime(2099, 1, 1, 12)),
            (datetime(2099, 1, 1, 6), datetime(2099, 1, 1, 12)),
            True,
        ),
        (
            (datetime(2099, 1, 1, 8), datetime(2099, 1, 1, 12)),
            (datetime(2099, 1, 1, 10), datetime(2099, 1, 1, 18)),
            True,
        ),
        (
            (datetime(2099, 1, 1, 8), datetime(2099, 1, 1, 12)),
            (datetime(2099, 1, 1, 11, 59), datetime(2099, 1, 1, 12)),
            True,
        ),
        (
            (datetime(2099, 1, 1, 8), datetime(2099, 1, 1, 12)),
            (datetime(2099, 1, 1, 12), datetime(2099, 1, 1, 18)),
            False,
        ),
    ],
)
def test_get_conflicting_shifts(tz, a_times, b_times, conflict_expected, event, volunteer):
    common = dict(signup_method_slug=InstantConfirmationSignupMethod.slug, event=event)
    aware = functools.partial(make_aware, timezone=tz)
    a = Shift.objects.create(
        start_time=aware(a_times[0]),
        end_time=aware(a_times[1]),
        meeting_time=aware(a_times[0]) - timedelta(minutes=15),
        **common
    )
    b = Shift.objects.create(
        start_time=aware(b_times[0]),
        end_time=aware(b_times[1]),
        meeting_time=aware(b_times[0]) - timedelta(minutes=15),
        **common
    )
    a_participation = LocalParticipation.objects.create(
        shift=a, user=volunteer, state=AbstractParticipation.States.CONFIRMED
    )
    expected = {a_participation} if conflict_expected else set()
    assert set(get_conflicting_participations(b, volunteer.as_participant())) == expected
