from django.urls import reverse

from ephios.core.models import AbstractParticipation, LocalParticipation
from ephios.core.signup.flow.builtin.participant import InstantConfirmSignupFlow


def test_getting_dispatched_state_is_overwritten_by_participant_signup(
    django_app, volunteer, planner, event
):
    shift = event.shifts.first()

    # create participation in getting-dispatched state
    participation = shift.signup_flow.get_or_create_participation_for(volunteer.as_participant())
    participation.state = AbstractParticipation.States.GETTING_DISPATCHED
    participation.save()

    # load to have the form in getting dispatched state
    response = django_app.get(
        reverse("core:shift_disposition", kwargs=dict(pk=shift.pk)),
        user=planner,
    )

    # meanwhile, request a participation as volunteer
    participation.state = AbstractParticipation.States.REQUESTED
    participation.save()

    # save the disposition, and assert that it doesn't overwrite the requested state
    response.forms["participations-form"].submit()
    assert (
        LocalParticipation.objects.get(user=volunteer, shift=shift).state
        == AbstractParticipation.States.REQUESTED
    )


def test_requested_participations_are_always_rendered(django_app, volunteer, planner, event):
    """
    regression test for https://github.com/ephios-dev/ephios/issues/633
    InstantConfirmationSignupMethod doesn't use the requested state, but a requested participation exists. Test that.
    """
    shift = event.shifts.first()
    shift.signup_flow_slug = InstantConfirmSignupFlow.slug
    shift.save()

    participation = shift.signup_flow.get_or_create_participation_for(volunteer.as_participant())
    participation.state = AbstractParticipation.States.REQUESTED
    participation.save()

    django_app.get(
        reverse("core:shift_disposition", kwargs=dict(pk=shift.pk)),
        user=planner,
    ).forms["participations-form"].submit()


def test_disposition_delete_participations_getting_dispatched(
    django_app, volunteer, planner, event
):
    # setup a participation
    shift = event.shifts.first()

    volunteer_participation = shift.signup_flow.get_or_create_participation_for(
        volunteer.as_participant()
    )
    volunteer_participation.state = AbstractParticipation.States.REQUESTED
    volunteer_participation.save()

    planner_participation = shift.signup_flow.get_or_create_participation_for(
        planner.as_participant()
    )
    planner_participation.state = AbstractParticipation.States.GETTING_DISPATCHED
    planner_participation.save()

    # delete the getting dispatched participation
    response = django_app.get(
        reverse("core:shift_disposition", kwargs=dict(pk=shift.pk)),
        user=planner,
    )
    form = response.forms["participations-form"]
    form["participations-0-state"] = AbstractParticipation.States.RESPONSIBLE_REJECTED.value
    form["participations-1-DELETE"] = True
    form.submit()

    assert (
        LocalParticipation.objects.get().state == AbstractParticipation.States.RESPONSIBLE_REJECTED
    )


def test_comment_is_only_visible_to_responsibles(
    django_app, planner, volunteer, qualified_volunteer, event
):
    # comment is also not visible for
    COMMENT_TEXT = "n.f.D. super secret comment text"
    response = django_app.get(event.get_absolute_url(), user=volunteer)
    form = response.form.submit(name="signup_choice", value="customize").form
    form["comment"] = COMMENT_TEXT
    response = form.submit(name="signup_choice", value="sign_up").follow()

    assert COMMENT_TEXT in response
    assert COMMENT_TEXT in django_app.get(event.get_absolute_url(), user=planner)
    assert COMMENT_TEXT not in django_app.get(event.get_absolute_url(), user=qualified_volunteer)
