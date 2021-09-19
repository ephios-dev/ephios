from collections import OrderedDict
from datetime import date, datetime

import pytest
from django.urls import reverse
from django.utils.timezone import make_aware

from ephios.core.models import Notification, UserProfile
from ephios.core.services.notifications.types import NewProfileNotification


class TestUserProfileView:
    def test_userprofile_list_permission_required(self, django_app, volunteer):
        response = django_app.get(reverse("core:userprofile_list"), user=volunteer, status=403)
        assert response.status_code == 403

    def test_userprofile_list(self, django_app, superuser):
        response = django_app.get(reverse("core:userprofile_list"), user=superuser)
        assert response.status_code == 200
        assert response.html.findAll(text=UserProfile.objects.all().values_list("email", flat=True))
        edit_links = [
            reverse("core:userprofile_edit", kwargs={"pk": userprofile_id})
            for userprofile_id in UserProfile.objects.all().values_list("id", flat=True)
        ]
        assert response.html.findAll("a", href=edit_links)

    def test_userprofile_create_permission_required(self, django_app, volunteer):
        response = django_app.get(reverse("core:userprofile_create"), user=volunteer, status=403)
        assert response.status_code == 403

    def test_userprofile_create(self, csrf_exempt_django_app, groups, manager, qualifications):
        managers, planners, volunteers = groups
        response = csrf_exempt_django_app.get(reverse("core:userprofile_create"), user=manager)
        assert response.status_code == 200
        userprofile_email = "testuser@localhost"

        POST_DATA = OrderedDict(
            {
                "email": userprofile_email,
                "first_name": "testfirst",
                "last_name": "testlast",
                "date_of_birth": "1999-01-01",
                "phone": "",
                "groups": volunteers.id,
                "is_active": "on",
                "qualification_grants": "",
                "qualification_grants-0-qualification": qualifications.rs.id,
                "qualification_grants-0-expires": "",
                "qualification_grants-1-qualification": qualifications.na.id,
                "qualification_grants-1-expires": "2030-01-01",
                "qualification_grants-INITIAL_FORMS": "0",
                "qualification_grants-MAX_NUM_FORMS": "1000",
                "qualification_grants-MIN_NUM_FORMS": "0",
                "qualification_grants-TOTAL_FORMS": "2",
            }
        )
        response = csrf_exempt_django_app.post(
            reverse("core:userprofile_create"),
            user=manager,
            params=POST_DATA,
        )

        assert response.status_code == 302
        userprofile = UserProfile.objects.get(email=userprofile_email)
        assert userprofile.email == userprofile_email
        assert Notification.objects.count() == 1
        assert Notification.objects.first().slug == NewProfileNotification.slug

        assert userprofile.first_name == "testfirst"
        assert userprofile.last_name == "testlast"
        assert userprofile.date_of_birth == date(1999, 1, 1)
        assert userprofile.phone == ""
        assert userprofile.is_active
        assert set(userprofile.groups.all()) == {volunteers}
        assert set(userprofile.qualifications) == {qualifications.rs, qualifications.na}
        assert userprofile.qualifications.get(id=qualifications.rs.id).expires is None
        assert userprofile.qualifications.get(id=qualifications.na.id).expires == make_aware(
            datetime.max.replace(2030, 1, 1)
        )

    def test_userprofile_edit(self, django_app, groups, manager, volunteer):
        userprofile = volunteer
        managers, planners, volunteers = groups
        response = django_app.get(
            reverse("core:userprofile_edit", kwargs={"pk": userprofile.id}), user=manager
        )
        form = response.form
        userprofile_email = "newmail@localhost"
        userprofile_phone = "12345"
        form["email"] = userprofile_email
        form["phone"] = userprofile_phone
        form["groups"].select_multiple(texts=["Volunteers", "Planners"])
        response = form.submit()
        assert response.status_code == 302
        userprofile.refresh_from_db()
        assert userprofile.email == userprofile_email
        assert set(userprofile.groups.all()) == {volunteers, planners}

    def test_userprofile_delete(self, django_app, groups, volunteer, manager):
        userprofile = volunteer
        response = django_app.get(
            reverse("core:userprofile_delete", kwargs={"pk": userprofile.id}),
            user=manager,
        )
        assert response.status_code == 200
        response = response.form.submit()
        assert response.status_code == 302
        with pytest.raises(UserProfile.DoesNotExist):
            UserProfile.objects.get(email=userprofile.email).exists()

    def test_userprofile_password_reset(self, django_app, groups, volunteer, manager):
        userprofile = volunteer
        response = django_app.get(
            reverse("core:userprofile_password_reset", kwargs={"pk": userprofile.id}),
            user=manager,
        )
        assert response.status_code == 200
        response.form.submit()
        assert response.status_code == 200

    def test_userprofile_edit_by_hr_allowed(self, django_app, volunteer, hr_group, groups):
        managers, planners, volunteers = groups
        form = django_app.get(
            reverse("core:userprofile_edit", kwargs={"pk": volunteer.id}), user=volunteer
        ).form
        form["groups"].force_value([volunteers.id])
        response = form.submit()
        assert response.status_code == 302
        assert set(volunteer.groups.all()) == {volunteers}

    def test_userprofile_edit_by_hr_forbidden(self, django_app, volunteer, hr_group, groups):
        managers, planners, volunteers = groups
        assert set(volunteer.groups.all()) == {hr_group, volunteers}
        form = django_app.get(
            reverse("core:userprofile_edit", kwargs={"pk": volunteer.id}), user=volunteer
        ).form
        form["groups"].force_value([managers.id])
        response = form.submit()
        assert response.status_code == 200
        assert set(volunteer.groups.all()) == {hr_group, volunteers}
