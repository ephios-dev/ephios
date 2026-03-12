import functools
from datetime import datetime, timedelta

import pytest
from django.utils import timezone
from django.utils.timezone import make_aware

from ephios.core.models import (
    AbstractParticipation,
    LocalParticipation,
    Qualification,
    QualificationGrant,
    Shift,
)
from ephios.core.signup.flow.participant_validation import (
    ParticipantUnfitError,
    get_conflicting_participations,
)
from ephios.core.signup.stats import SignupStats
from ephios.plugins.baseshiftstructures.structure.uniform import UniformShiftStructure
from ephios.plugins.basesignupflows.flow.participant import InstantConfirmSignupFlow


def test_signup_stats_addition():
    a = SignupStats(4, 2, 3, None, 5, None)
    b = SignupStats(5, 2, 3, 5, 5, 7)
    c = SignupStats(3, 2, 0, 2, None, 4)
    assert a + b == SignupStats(9, 4, 6, None, 10, None)
    assert b + c == SignupStats(8, 4, 3, 7, 5, 11)


def test_signup_stats_full_count():
    # default case
    a = SignupStats(
        requested_count=0,
        confirmed_count=4,
        min_count=4,
        max_count=6,
        missing=0,
        free=2,
    )
    assert a.full_count == 6
    assert a.required_count == 4

    # overbooked with someone unqualified
    b = SignupStats(
        requested_count=0,
        confirmed_count=6,
        min_count=6,
        max_count=7,
        missing=1,
        free=2,
    )
    assert b.full_count == 8
    assert b.required_count == 7


def test_participant_unfit_is_not_the_same_as_signup_errors(event, qualified_volunteer):
    shift: Shift = event.shifts.first()
    shift.signup_flow_configuration["signup_until"] = timezone.make_aware(
        datetime.min.replace(year=2020)
    )
    shift.save()
    assert not list(
        filter(
            lambda error: isinstance(error, ParticipantUnfitError),
            shift.signup_flow.get_validator(
                qualified_volunteer.as_participant()
            ).get_signup_errors(),
        )
    )
    assert shift.signup_flow.get_validator(qualified_volunteer.as_participant()).get_signup_errors()


def test_cannot_sign_up_for_conflicting_shifts(django_app, volunteer, event, conflicting_event):
    assert (
        not conflicting_event.shifts
        .first()
        .signup_flow.get_validator(volunteer.as_participant())
        .can_sign_up()
    )


def test_partially_conflicting_shift_results_in_invalid_signup_form(
    django_app, volunteer, event, conflicting_event
):
    assert "already confirmed" in django_app.get(
        event.get_absolute_url(),
        user=volunteer,
    )
    # make the conflicting shift not cover the shift we want to participate in
    shift_b = conflicting_event.shifts.first()
    shift_b.end_time -= timedelta(hours=1)
    shift_b.save()
    response = (
        django_app
        .get(
            event.get_absolute_url(),
            user=volunteer,
        )
        .form.submit(name="signup_choice", value="sign_up")
        .follow()
    )
    assert "Please check that your individual start and end times" in response
    # move start to after the conflicting event ended
    response.form["individual_start_time_1"] = "19:42"
    assert (
        "successfully requested a participation"
        in response.form.submit(name="signup_choice", value="sign_up").follow()
    )


@pytest.mark.parametrize(
    "a_times,b_times,conflict_expected,total",
    [
        (
            (datetime(2099, 1, 1, 8), datetime(2099, 1, 1, 12)),
            (datetime(2099, 1, 1, 6), datetime(2099, 1, 1, 8)),
            False,
            False,
        ),
        (
            (datetime(2099, 1, 1, 8), datetime(2099, 1, 1, 12)),
            (datetime(2099, 1, 1, 6), datetime(2099, 1, 1, 10)),
            True,
            False,
        ),
        (
            (datetime(2099, 1, 1, 8), datetime(2099, 1, 1, 12)),
            (datetime(2099, 1, 1, 6), datetime(2099, 1, 1, 12)),
            True,
            False,
        ),
        (
            (datetime(2099, 1, 1, 8), datetime(2099, 1, 1, 12)),
            (datetime(2099, 1, 1, 10), datetime(2099, 1, 1, 18)),
            True,
            False,
        ),
        (
            (datetime(2099, 1, 1, 8), datetime(2099, 1, 1, 12)),
            (datetime(2099, 1, 1, 11, 59), datetime(2099, 1, 1, 12)),
            True,
            False,
        ),
        (
            (datetime(2099, 1, 1, 8), datetime(2099, 1, 1, 12)),
            (datetime(2099, 1, 1, 12), datetime(2099, 1, 1, 18)),
            False,
            False,
        ),
        (
            (datetime(2099, 1, 1, 8), datetime(2099, 1, 1, 12)),
            (datetime(2099, 1, 1, 11), datetime(2099, 1, 1, 14)),
            False,
            True,
        ),
        (
            (datetime(2099, 1, 1, 8), datetime(2099, 1, 1, 12)),
            (datetime(2099, 1, 1, 10), datetime(2099, 1, 1, 11)),
            True,
            True,
        ),
    ],
)
def test_get_conflicting_shifts(tz, a_times, b_times, conflict_expected, total, event, volunteer):
    common = dict(
        signup_flow_slug=InstantConfirmSignupFlow.slug,
        structure_slug=UniformShiftStructure.slug,
        event=event,
    )
    aware = functools.partial(make_aware, timezone=tz)
    a = Shift.objects.create(
        start_time=aware(a_times[0]),
        end_time=aware(a_times[1]),
        meeting_time=aware(a_times[0]) - timedelta(minutes=15),
        **common,
    )
    b = Shift.objects.create(
        start_time=aware(b_times[0]),
        end_time=aware(b_times[1]),
        meeting_time=aware(b_times[0]) - timedelta(minutes=15),
        **common,
    )
    a_participation = LocalParticipation.objects.create(
        shift=a, user=volunteer, state=AbstractParticipation.States.CONFIRMED
    )
    expected = {a_participation} if conflict_expected else set()
    assert (
        set(
            get_conflicting_participations(
                participant=volunteer.as_participant(),
                shift=b,
                total=total,
            )
        )
        == expected
    )


def test_get_conflicting_shift_with_individual_time(tz, volunteer, multi_shift_event):
    shift_a, shift_b = multi_shift_event.shifts.order_by("start_time")
    a_participation = LocalParticipation.objects.create(
        shift=shift_a,
        user=volunteer,
        state=AbstractParticipation.States.CONFIRMED,
        individual_start_time=shift_a.start_time,
        individual_end_time=shift_b.start_time + timedelta(minutes=30),
    )
    assert set(get_conflicting_participations(volunteer.as_participant(), shift_b)) == {
        a_participation
    }


def test_event_detail_renders_with_missing_signup_flow(django_app, event, volunteer):
    shift: Shift = event.shifts.first()
    shift.signup_flow_slug = "some_missing_slug_that_doesnt_exist"
    shift.save()
    assert "invalid" in django_app.get(
        event.get_absolute_url(),
        user=volunteer,
    )


def test_general_required_qualifications(django_app, event, volunteer, qualifications):
    event.type.preferences["general_required_qualifications"] = Qualification.objects.filter(
        pk=qualifications.b.pk
    )
    assert (
        not event.shifts.first().signup_flow.get_validator(volunteer.as_participant()).can_sign_up()
    )
    QualificationGrant.objects.create(qualification=qualifications.b, user=volunteer)
    volunteer.refresh_from_db()
    assert event.shifts.first().signup_flow.get_validator(volunteer.as_participant()).can_sign_up()
