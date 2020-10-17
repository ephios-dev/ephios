from datetime import date

import pytest
from django.contrib.auth.models import Group
from ephios.user_management.models import UserProfile
from django.urls import reverse
from guardian.shortcuts import get_group_perms


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
        response = django_app.get(reverse("user_management:userprofile_create"), user=manager)
        form = response.form
        userprofile_email = "testuser@localhost"
        userprofile_first_name = "testfirst"
        userprofile_last_name = "testlast"
        form["email"] = userprofile_email
        form["first_name"] = userprofile_first_name
        form["last_name"] = userprofile_last_name
        form["date_of_birth"] = date(1999, 1, 1)
        form["groups"].force_value(3)
        response = form.submit()
        assert response.status_code == 302
        userprofile = UserProfile.objects.get(email=userprofile_email)
        assert not userprofile.user_permissions.filter(codename="view_past_event").exists()
        assert not userprofile.user_permissions.filter(codename="add_event").exists()

    # def test_group_create_with_permissions(self, django_app, groups, manager):
    #     response = django_app.get(reverse("user_management:group_add"), user=manager)
    #     form = response.form
    #     group_name = "Testgroup"
    #     form["name"] = group_name
    #     form["users"].force_value([manager.id])
    #     form["can_view_past_event"] = True
    #     form["can_add_event"] = True
    #     form["publish_event_for_group"].select_multiple(texts=["Volunteers"])
    #     response = form.submit()
    #     assert response.status_code == 302
    #     group = Group.objects.get(name=group_name)
    #     assert set(group.user_set.all()) == {manager}
    #     assert group.permissions.filter(codename="view_past_event").exists()
    #     assert group.permissions.filter(codename="add_event").exists()
    #     assert "publish_event_for_group" in get_group_perms(
    #         group, Group.objects.get(name="Volunteers")
    #     )
    #
    # def test_group_edit(self, django_app, groups, manager):
    #     group = manager.groups.first()
    #     response = django_app.get(
    #         reverse("user_management:group_edit", kwargs={"pk": group.id}), user=manager
    #     )
    #     form = response.form
    #     group_name = "New name"
    #     form["name"] = group_name
    #     form["users"].force_value([manager.id])
    #     form["can_view_past_event"] = False
    #     form["can_add_event"] = False
    #     form["publish_event_for_group"].select_multiple(texts=["Volunteers"])
    #     response = form.submit()
    #     assert response.status_code == 302
    #     group.refresh_from_db()
    #     assert group.name == group_name
    #     assert set(group.user_set.all()) == {manager}
    #     assert not group.permissions.filter(codename="view_past_event").exists()
    #     assert not group.permissions.filter(codename="add_event").exists()
    #     assert "publish_event_for_group" not in get_group_perms(
    #         group, Group.objects.get(name="Volunteers")
    #     )
    #
    # def test_group_delete(self, django_app, groups, manager):
    #     group = Group(name="Testgroup")
    #     group.save()
    #     response = django_app.get(
    #         reverse("user_management:group_delete", kwargs={"pk": group.id}), user=manager
    #     )
    #     assert response.status_code == 200
    #     response = response.form.submit()
    #     assert response.status_code == 302
    #     with pytest.raises(Group.DoesNotExist):
    #         Group.objects.get(name=group.name).exists()
