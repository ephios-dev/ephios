import pytest

from ephios.core.signup import SignupStats


@pytest.mark.django_db
def test_signup_stats_addition(django_app):
    a = SignupStats(4, 2, 3, None)
    b = SignupStats(5, 2, 3, 5)
    c = SignupStats(3, 2, None, 2)
    assert a + b == SignupStats(9, 4, 6, None)
    assert b + c == SignupStats(8, 4, 3, 7)


@pytest.mark.django_db
def test_signup_conflicting_shifts(django_app, volunteer, event, conflicting_event):
    assert not conflicting_event.shifts.first().signup_method.can_sign_up(
        volunteer.as_participant()
    )
