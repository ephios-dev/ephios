import pytest
from django.urls import reverse

from ephios.core.models import AbstractParticipation, LocalParticipation


@pytest.mark.django_db
def test_single_shift_pdf(django_app, planner, event, volunteer):
    response_no_participations = django_app.get(
        reverse("core:event_detail_pdf", kwargs=dict(pk=event.pk)),
        user=planner,
    )
    assert response_no_participations
    LocalParticipation.objects.create(
        shift=event.shifts.first(), user=volunteer, state=AbstractParticipation.States.CONFIRMED
    )
    response = django_app.get(
        reverse("core:event_detail_pdf", kwargs=dict(pk=event.pk)),
        user=planner,
    )
    assert response and response != response_no_participations


@pytest.mark.django_db
def test_multi_shift_pdf(django_app, planner, multi_shift_event, volunteer):
    response_no_participations = django_app.get(
        reverse("core:event_detail_pdf", kwargs=dict(pk=multi_shift_event.pk)),
        user=planner,
    )
    assert response_no_participations
    LocalParticipation.objects.create(
        shift=multi_shift_event.shifts.first(),
        user=volunteer,
        state=AbstractParticipation.States.CONFIRMED,
    )
    LocalParticipation.objects.create(
        shift=multi_shift_event.shifts.last(),
        user=volunteer,
        state=AbstractParticipation.States.CONFIRMED,
    )
    response = django_app.get(
        reverse("core:event_detail_pdf", kwargs=dict(pk=multi_shift_event.pk)),
        user=planner,
    )
    assert response and response != response_no_participations
