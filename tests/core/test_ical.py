import pytest
from django.urls import reverse

from ephios.core.models import AbstractParticipation


@pytest.mark.django_db
def test_user_event_feed(django_app, qualified_volunteer, event):
    response = django_app.get(
        reverse("core:event_detail", kwargs=dict(pk=event.pk)), user=qualified_volunteer
    )
    response.form.submit(name="signup_choice", value="sign_up")

    # the event feed should work, but not contain participations in state REQUESTED
    response = django_app.get(
        reverse(
            "core:user_event_feed", kwargs=dict(calendar_token=qualified_volunteer.calendar_token)
        )
    )
    assert response and event.title not in response

    # only after getting confirmed the feed should contain the event
    participation = AbstractParticipation.objects.last()
    participation.state = AbstractParticipation.States.CONFIRMED
    participation.save()
    response = django_app.get(
        reverse(
            "core:user_event_feed", kwargs=dict(calendar_token=qualified_volunteer.calendar_token)
        )
    )
    assert response and event.title in response
