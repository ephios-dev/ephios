from datetime import timedelta

from django.urls import reverse

from ephios.core.models import AbstractParticipation


def test_user_event_feed(django_app, qualified_volunteer, event):
    # the event feed should work, but not contain the event
    response = django_app.get(
        reverse(
            "core:user_event_feed", kwargs=dict(calendar_token=qualified_volunteer.calendar_token)
        )
    )
    assert response and event.title not in response

    response = django_app.get(event.get_absolute_url(), user=qualified_volunteer)
    response.form.submit(name="signup_choice", value="sign_up")

    # requested maps to tentative state
    response = django_app.get(
        reverse(
            "core:user_event_feed", kwargs=dict(calendar_token=qualified_volunteer.calendar_token)
        )
    )
    assert event.title in response
    assert "STATUS:TENTATIVE" in response

    # only after getting confirmed the feed should contain the event as CONFIRMED
    participation = AbstractParticipation.objects.last()
    participation.state = AbstractParticipation.States.CONFIRMED
    individual_start_time = event.shifts.first().start_time + timedelta(minutes=53)
    participation.individual_start_time = individual_start_time
    participation.save()
    response = django_app.get(
        reverse(
            "core:user_event_feed", kwargs=dict(calendar_token=qualified_volunteer.calendar_token)
        )
    )
    assert "TENTATIVE" not in response
    assert individual_start_time.strftime("%M") in response
