from datetime import date

import pytest
from django.urls import reverse

from ephios.user_management.models import UserProfile


@pytest.mark.django_db
class TestUserProfileView:
    def test_userprofile_list_permission_required(self, django_app, volunteer):
        response = django_app.get(
            reverse("user_management:userprofile_list"), user=volunteer, status=403
        )
        assert response.status_code == 403

    def test_userprofile_list(self, django_app, superuser):
        response = django_app.get(reverse("user_management:userprofile_list"), user=superuser)
        assert response.status_code == 200
        assert response.html.findAll(text=UserProfile.objects.all().values_list("email", flat=True))
        edit_links = [
            reverse("user_management:userprofile_edit", kwargs={"pk": userprofile_id})
            for userprofile_id in UserProfile.objects.all().values_list("id", flat=True)
        ]
        assert response.html.findAll("a", href=edit_links)

    def test_userprofile_create_permission_required(self, django_app, volunteer):
        response = django_app.get(
            reverse("user_management:userprofile_create"), user=volunteer, status=403
        )
        assert response.status_code == 403

    def test_userprofile_create(self, django_app, groups, manager):
        managers, planners, volunteers = groups
        response = django_app.get(reverse("user_management:userprofile_create"), user=manager)
        form = response.form
        userprofile_email = "testuser@localhost"
        userprofile_first_name = "testfirst"
        userprofile_last_name = "testlast"
        form["email"] = userprofile_email
        form["first_name"] = userprofile_first_name
        form["last_name"] = userprofile_last_name
        form["date_of_birth"] = date(1999, 1, 1)
        form["groups"].select_multiple(texts=["Volunteers"])
        response = form.submit()
        assert response.status_code == 302
        userprofile = UserProfile.objects.get(email=userprofile_email)
        assert userprofile.email == userprofile_email

    def test_userprofile_edit(self, django_app, groups, manager, volunteer):
        userprofile = volunteer
        managers, planners, volunteers = groups
        response = django_app.get(
            reverse("user_management:userprofile_edit", kwargs={"pk": userprofile.id}), user=manager
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
        userprofile.save()
        response = django_app.get(
            reverse("user_management:userprofile_delete", kwargs={"pk": userprofile.id}),
            user=manager,
        )
        assert response.status_code == 200
        response = response.form.submit()
        assert response.status_code == 302
        with pytest.raises(UserProfile.DoesNotExist):
            UserProfile.objects.get(email=userprofile.email).exists()
