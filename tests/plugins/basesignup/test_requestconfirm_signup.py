from django.urls import reverse
from guardian.shortcuts import get_users_with_perms

from ephios.core.models import AbstractParticipation, LocalParticipation


def test_request_confirm_signup_flow(django_app, volunteer, planner, event):
    # request a participation as volunteer
    assert volunteer in get_users_with_perms(event, only_with_perms_in=["view_event"])
    response = django_app.get(event.get_absolute_url(), user=volunteer)
    response.form.submit(name="signup_choice", value="sign_up")
    shift = event.shifts.first()
    assert (
        LocalParticipation.objects.get(user=volunteer, shift=shift).state
        == AbstractParticipation.States.REQUESTED
    )

    response = django_app.get(event.get_absolute_url(), user=volunteer)
    assert "already requested" in response

    # confirm the participation as planner
    response = django_app.get(
        reverse("core:shift_disposition", kwargs=dict(pk=shift.pk)),
        user=planner,
    )
    form = response.forms["participations-form"]
    form["participations-0-state"] = AbstractParticipation.States.CONFIRMED.value
    form.submit()
    assert (
        LocalParticipation.objects.get(user=volunteer, shift=shift).state
        == AbstractParticipation.States.CONFIRMED
    )


def test_request_confirm_decline_flow(django_app, volunteer, planner, event):
    # decline a participation as volunteer
    assert volunteer in get_users_with_perms(event, only_with_perms_in=["view_event"])
    response = django_app.get(event.get_absolute_url(), user=volunteer)
    response.form.submit(name="signup_choice", value="decline")
    shift = event.shifts.first()
    assert (
        LocalParticipation.objects.get(user=volunteer, shift=shift).state
        == AbstractParticipation.States.USER_DECLINED
    )

    response = django_app.get(event.get_absolute_url(), user=volunteer)
    assert "already declined" in response


def test_request_confirm_add_user_in_disposition(django_app, volunteer, planner, event):
    # confirm the participation as planner
    shift = event.shifts.first()
    form = django_app.get(
        reverse("core:shift_disposition", kwargs=dict(pk=shift.pk)),
        user=planner,
    ).forms["add-user-form"]
    # can't user form.submit as webtest doesn't recognise the user field (as that's outside of the <form> tags)
    response = django_app.post(
        form.action,
        user=planner,
        params={
            "csrfmiddlewaretoken": form["csrfmiddlewaretoken"].value,
            "user": volunteer.id,
            "new_index": 0,
        },
    )
    assert volunteer.first_name in response
    assert volunteer.as_participant().participation_for(shift) is not None
