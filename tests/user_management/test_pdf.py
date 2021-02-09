from datetime import datetime

import pytest
from django.urls import reverse

from ephios.plugins.basesignup.signup.request_confirm import RequestConfirmSignupMethod
from ephios.user_management.models import Shift


@pytest.mark.django_db
def test_single_shift_pdf(django_app, planner, event):
    response = django_app.get(
        reverse("user_management:event_detail_pdf", kwargs=dict(pk=event.pk)),
        user=planner,
    )
    assert response


@pytest.mark.django_db
def test_multi_shift_pdf(django_app, planner, event, tz):
    Shift.objects.create(
        event=event,
        meeting_time=datetime(2099, 7, 1, 7, 0).astimezone(tz),
        start_time=datetime(2099, 7, 1, 8, 0).astimezone(tz),
        end_time=datetime(2099, 7, 1, 20, 0).astimezone(tz),
        signup_method_slug=RequestConfirmSignupMethod.slug,
        signup_configuration={},
    )
    response = django_app.get(
        reverse("user_management:event_detail_pdf", kwargs=dict(pk=event.pk)),
        user=planner,
    )
    assert response
