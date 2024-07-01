import pytest
from django.urls import reverse

from ephios.core.signup.flow.builtin.manual import ManualSignupFlow


@pytest.fixture
def manual_sign_shift(event):
    shift = event.shifts.get()
    shift.signup_flow_slug = ManualSignupFlow.slug
    shift.save()
    return shift


def test_configuring_manual_sign_shift(django_app, planner, manual_sign_shift):
    response = django_app.get(
        reverse("core:shift_edit", kwargs={"pk": manual_sign_shift.pk}), user=planner
    )
    response.form["no_selfservice_explanation"] = "this is just a test"
    assert "this is just a test" in response.form.submit().follow()


def test_manual_sign_renders(django_app, volunteer, event, manual_sign_shift):
    response = django_app.get(event.get_absolute_url(), user=volunteer)
    assert "Signup for this shift is disabled." in response


def test_manual_sign_does_not_allow_signup(django_app, volunteer, event, manual_sign_shift):
    event_detail = django_app.get(event.get_absolute_url(), user=volunteer).form.submit()
    assert not volunteer.participations.exists()
