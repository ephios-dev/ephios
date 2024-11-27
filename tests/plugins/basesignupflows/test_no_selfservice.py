import pytest
from django.urls import reverse

from ephios.plugins.basesignupflows.flow.manual import ManualSignupFlow


@pytest.fixture
def manual_signup_shift(event):
    shift = event.shifts.get()
    shift.signup_flow_slug = ManualSignupFlow.slug
    shift.save()
    return shift


def test_configuring_manual_signup_shift(django_app, planner, manual_signup_shift):
    response = django_app.get(
        reverse("core:shift_edit", kwargs={"pk": manual_signup_shift.pk}), user=planner
    )
    response.form["no_selfservice_explanation"] = "this is just a test"
    assert "this is just a test" in response.form.submit().follow()


def test_manual_signup_renders(django_app, volunteer, event, manual_signup_shift):
    response = django_app.get(event.get_absolute_url(), user=volunteer)
    assert "Signup for this shift is disabled." in response
