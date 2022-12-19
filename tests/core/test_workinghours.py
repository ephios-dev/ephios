import datetime
import re

from django.template.defaultfilters import floatformat
from django.urls import reverse

from ephios.core.models import WorkingHours


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
            user=volunteer,
            shift=event.shifts.first(),
            state=AbstractParticipation.States.CONFIRMED,
            finished=True,
        )
        hour_sum, workinghour_list = volunteer.get_workhour_items()
        assert hour_sum == datetime.timedelta(hours=12.5)

    def test_workinghour_overview(self, django_app, superuser, volunteer, workinghours):
        response = django_app.get(reverse("core:workinghour_list"), user=superuser)
        assert response.html.find(text=floatformat(workinghours[1].hours, arg=2))
        assert not response.html.find(text=superuser.last_name)

    def test_grant_permission(
        self, django_app, manager, superuser, groups, workinghours, volunteer
    ):
        WorkingHours.objects.create(
            date=datetime.date.today(), user=superuser, hours=1, reason="test"
        )
        response = django_app.get(reverse("core:workinghour_list"), user=volunteer, status=403)
        response = django_app.get(reverse("core:workinghour_list"), user=manager)
        assert len(response.html.find_all("span", text=re.compile("^Add$"))) == 1
        response = django_app.get(reverse("core:workinghour_list"), user=superuser)
        assert len(response.html.find_all("span", text=re.compile("^Add$"))) == 2

    def test_workinghour_delete(self, django_app, superuser, volunteer, workinghours, groups):
        response = django_app.get(
            reverse("core:workinghour_delete", kwargs={"pk": workinghours[0].pk}), user=superuser
        )
        response.form.submit()
        assert not WorkingHours.objects.filter(pk=workinghours[0].pk).exists()

    def test_workinghour_edit(self, django_app, superuser, volunteer, workinghours, groups):
        response = django_app.get(
            reverse("core:workinghour_edit", kwargs={"pk": workinghours[0].pk}), user=superuser
        )
        response.form["hours"] = 2
        response.form.submit()
        assert WorkingHours.objects.get(pk=workinghours[0].pk).hours == 2
