import datetime
import re

from django.template.defaultfilters import floatformat
from django.urls import reverse

from ephios.core.models import LocalParticipation, WorkingHours


class TestWorkingHours:
    def test_own_workinghours_without_hours(self, django_app, volunteer):
        response = django_app.get(reverse("core:workinghours_own"), user=volunteer)
        assert response.status_code == 200
        assert response.html.find(string=f"{floatformat(0, arg=2)}")

    def test_own_workinghours(self, django_app, volunteer, workinghours):
        response = django_app.get(reverse("core:workinghours_own"), user=volunteer)
        assert response.html.find(string=workinghours[0].reason)
        assert response.html.find(string=workinghours[1].reason)
        total_hours = workinghours[0].hours + workinghours[1].hours
        assert response.html.find(string=f"{floatformat(total_hours, arg=2)}")

    def test_workinghours_rounding(self, django_app, volunteer, event):
        from ephios.core.models import AbstractParticipation, LocalParticipation

        LocalParticipation.objects.create(
            user=volunteer,
            shift=event.shifts.first(),
            state=AbstractParticipation.States.CONFIRMED,
            finished=True,
        )
        hour_sum, workinghours_list = volunteer.get_workhour_items()
        assert hour_sum == datetime.timedelta(hours=12.5)

    def test_workinghours_overview(self, django_app, superuser, volunteer, workinghours):
        response = django_app.get(reverse("core:workinghours_list"), user=superuser)
        assert response.html.find(string=floatformat(workinghours[1].hours, arg=2))
        assert not response.html.find(string=superuser.display_name)

    def test_grant_permission(
        self, django_app, manager, superuser, groups, workinghours, volunteer
    ):
        WorkingHours.objects.create(
            date=datetime.date.today(), user=superuser, hours=1, reason="test"
        )
        response = django_app.get(reverse("core:workinghours_list"), user=volunteer, status=403)
        response = django_app.get(reverse("core:workinghours_list"), user=manager)
        assert len(response.html.find_all("span", string=re.compile("^Add$"))) == 1
        response = django_app.get(reverse("core:workinghours_list"), user=superuser)
        assert len(response.html.find_all("span", string=re.compile("^Add$"))) == 2

    def test_workinghours_delete(self, django_app, superuser, volunteer, workinghours, groups):
        response = django_app.get(
            reverse("core:workinghours_delete", kwargs={"pk": workinghours[0].pk}), user=superuser
        )
        response.form.submit()
        assert not WorkingHours.objects.filter(pk=workinghours[0].pk).exists()

    def test_workinghours_edit(self, django_app, superuser, volunteer, workinghours, groups):
        response = django_app.get(
            reverse("core:workinghours_edit", kwargs={"pk": workinghours[0].pk}), user=superuser
        )
        response.form["hours"] = 2
        response.form.submit()
        assert WorkingHours.objects.get(pk=workinghours[0].pk).hours == 2

    def test_workinghours_detail(self, django_app, superuser, volunteer, workinghours, groups):
        response = django_app.get(
            reverse("core:workinghours_detail", kwargs={"pk": workinghours[0].user.pk}),
            user=superuser,
        )
        assert response.html.find(string=workinghours[0].reason)

    def test_workinghours_detail_nologin(self, django_app, workinghours):
        response = django_app.get(
            reverse("core:workinghours_detail", kwargs={"pk": workinghours[0].user.pk}),
            status=302,
        )
        assert "/accounts/login" in response.url

    def test_workinghours_add(self, django_app, superuser, volunteer, groups):
        response = django_app.get(
            reverse("core:workinghours_add", kwargs={"pk": volunteer.pk}), user=superuser
        )
        response.form["date"] = datetime.date(2020, 1, 1)
        response.form["hours"] = 1
        response.form["reason"] = "new years cleanup"
        response.form.submit()
        assert WorkingHours.objects.filter(user=volunteer, reason="new years cleanup").exists()

    def test_workinghours_add_nologin(self, django_app, volunteer):
        response = django_app.get(
            reverse("core:workinghours_add", kwargs={"pk": volunteer.pk}), status=302
        )
        assert "/accounts/login" in response.url

    def test_workinghours_filter(
        self,
        django_app,
        volunteer,
        manager,
        event,
        service_event_type,
        training_event_type,
        workinghours,
    ):
        response = django_app.get(reverse("core:workinghours_list"), user=manager)
        assert response.html.find(
            string=floatformat(volunteer.get_workhour_items()[1][0]["duration"], arg=2)
        )
        participation = LocalParticipation.objects.create(
            shift=event.shifts.first(), user=volunteer, state=LocalParticipation.States.CONFIRMED
        )
        response = django_app.get(
            f"{reverse('core:workinghours_list')}?type={training_event_type.pk}", user=manager
        )
        assert response.html.find(string="No entries")
        response = django_app.get(
            f"{reverse('core:workinghours_list')}?type={service_event_type.pk}", user=manager
        )
        assert response.html.find(string=floatformat(participation.hours_value, arg=2))
