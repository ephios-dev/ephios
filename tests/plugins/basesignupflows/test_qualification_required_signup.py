from guardian.shortcuts import get_users_with_perms

from ephios.core.models import AbstractParticipation, LocalParticipation


def test_unqualified_cannot_signup(django_app, volunteer, event_with_required_qualification):
    assert volunteer in get_users_with_perms(
        event_with_required_qualification, only_with_perms_in=["view_event"]
    )
    response = django_app.get(event_with_required_qualification.get_absolute_url(), user=volunteer)
    assert "You are not qualified" in response


def test_qualified_can_signup(django_app, qualified_volunteer, event_with_required_qualification):
    assert qualified_volunteer in get_users_with_perms(
        event_with_required_qualification, only_with_perms_in=["view_event"]
    )
    response = django_app.get(
        event_with_required_qualification.get_absolute_url(), user=qualified_volunteer
    )
    response.form.submit(name="signup_choice", value="sign_up")

    shift = event_with_required_qualification.shifts.first()
    assert (
        LocalParticipation.objects.get(user=qualified_volunteer, shift=shift).state
        == AbstractParticipation.States.REQUESTED
    )
