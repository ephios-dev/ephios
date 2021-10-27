import pytest

from ephios.plugins.basesignup.signup.no_selfservice import NoSelfserviceSignupMethod


@pytest.fixture
def no_selfservice_shift(event):
    shift = event.shifts.get()
    shift.signup_method_slug = NoSelfserviceSignupMethod.slug
    shift.save()
    return shift


def test_no_selfservice_renders(django_app, volunteer, event, no_selfservice_shift):
    response = django_app.get(event.get_absolute_url(), user=volunteer)
    assert "Signup for this shift is disabled." in response


def test_no_selfservice_does_not_allow_signup(django_app, volunteer, event, no_selfservice_shift):
    event_detail = django_app.get(event.get_absolute_url(), user=volunteer)
    # django webtest would ignore a `signup_choice` on the event_detail view, so we just get the default sign up view
    signup_view = event_detail.form.submit()
    # from there though, signup will not be possible
    assert (
        "Signup for this shift is disabled"
        in signup_view.form.submit(name="signup_choice", value="sign_up").follow()
    )
