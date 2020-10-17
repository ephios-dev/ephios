import pytest
from django.urls import reverse
from guardian.shortcuts import get_users_with_perms

from ephios.event_management.models import AbstractParticipation, LocalParticipation


@pytest.mark.django_db
def test_request_confirm_flow(django_app, volunteer, planner, event):
    # request a participation as volunteer
    assert volunteer in get_users_with_perms(event, only_with_perms_in=["view_event"])
    response = django_app.get(
        reverse("event_management:event_detail", kwargs=dict(pk=event.pk)), user=volunteer
    )
    response.form.submit(name="signup_choice", value="sign_up")
    shift = event.shifts.first()
    assert LocalParticipation.objects.get(user=volunteer, shift=shift) is not None

    # confirm the participation as planner
    response = django_app.get(
        reverse("basesignup:shift_disposition_requestconfirm", kwargs=dict(pk=shift.pk)),
        user=planner,
    )
    response.form["form-0-state"] = AbstractParticipation.States.CONFIRMED.value
    response.form.submit()
    assert (
        LocalParticipation.objects.get(user=volunteer, shift=shift).state
        == AbstractParticipation.States.CONFIRMED
    )
