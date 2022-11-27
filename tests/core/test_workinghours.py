import datetime

from django.template.defaultfilters import floatformat
from django.urls import reverse


class TestWorkingHours:
    def test_own_workinghours_without_hours(self, django_app, volunteer):
        response = django_app.get(reverse("core:workinghour_own"), user=volunteer)
        assert response.status_code == 200
        assert response.html.find(text=f"{floatformat(0, arg=2)} hours")

    def test_own_workinghours(self, django_app, volunteer, workinghours):
        response = django_app.get(reverse("core:workinghour_own"), user=volunteer)
        assert response.html.find(text=workinghours[0].reason)
        assert response.html.find(text=workinghours[1].reason)
        total_hours = workinghours[0].hours + workinghours[1].hours
        assert response.html.find(text=f"{floatformat(total_hours, arg=2)} hours")

    def test_workinghour_rounding(self, django_app, volunteer, event):
        from ephios.core.models import AbstractParticipation, LocalParticipation

        LocalParticipation.objects.create(
            user=volunteer, shift=event.shifts.first(), state=AbstractParticipation.States.CONFIRMED
        )
        hour_sum, workinghour_list = volunteer.get_workhour_items()
        assert hour_sum == datetime.timedelta(hours=12.5)
