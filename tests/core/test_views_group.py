import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from guardian.shortcuts import get_group_perms

from ephios.core.forms.users import MANAGEMENT_PERMISSIONS
from ephios.extra.permissions import get_groups_with_perms


class TestGroupView:
    def test_group_list_permission_required(self, django_app, volunteer):
        response = django_app.get(reverse("core:group_list"), user=volunteer, status=403)
        assert response.status_code == 403

    def test_group_list(self, django_app, superuser, groups):
        response = django_app.get(reverse("core:group_list"), user=superuser)
        assert response.status_code == 200
        for group_name in Group.objects.all().values_list("name", flat=True):
            assert group_name in response.text
        edit_links = [
            reverse("core:group_edit", kwargs={"pk": group_id})
            for group_id in Group.objects.all().values_list("id", flat=True)
        ]
        assert response.html.find_all("a", href=edit_links)

    def test_group_create_permission_required(self, django_app, volunteer):
        response = django_app.get(reverse("core:group_add"), user=volunteer, status=403)
        assert response.status_code == 403

    def test_group_create(self, django_app, groups, manager):
        response = django_app.get(reverse("core:group_add"), user=manager)
        form = response.form
        group_name = "Testgroup"
        form["name"] = group_name
        form["users"].force_value([manager.id])
        response = form.submit()
        assert response.status_code == 302
        group = Group.objects.get(name=group_name)
        assert list(group.user_set.all()) == [manager]
        assert not group.permissions.filter(codename="add_event").exists()
        assert not group.permissions.filter(
            codename__in=[
                "add_userprofile",
                "change_userprofile",
                "delete_userprofile",
                "view_userprofile",
            ]
        ).exists()
        assert not group.permissions.filter(
            codename__in=[
                "add_group",
                "change_group",
                "delete_group",
                "view_group",
            ]
        ).exists()

    def test_group_create_with_permissions(self, django_app, groups, manager):
        response = django_app.get(reverse("core:group_add"), user=manager)
        form = response.form
        group_name = "Testgroup"
        form["name"] = group_name
        form["users"].force_value([manager.id])
        form["is_planning_group"] = True
        form["publish_event_for_group"].select_multiple(texts=["Volunteers"])
        form["is_hr_group"] = True
        form["is_management_group"] = True
        response = form.submit()
        assert response.status_code == 302
        group = Group.objects.get(name=group_name)
        assert set(group.user_set.all()) == {manager}
        assert group.permissions.filter(codename="add_event").exists()
        assert "publish_event_for_group" in get_group_perms(
            group, Group.objects.get(name="Volunteers")
        )
        assert group.permissions.filter(codename="add_userprofile").exists()
        assert group.permissions.filter(codename="change_userprofile").exists()
        assert group.permissions.filter(codename="delete_userprofile").exists()
        assert group.permissions.filter(codename="view_userprofile").exists()
        assert group.permissions.filter(codename="add_group").exists()
        assert group.permissions.filter(codename="change_group").exists()
        assert group.permissions.filter(codename="delete_group").exists()
        assert group.permissions.filter(codename="view_group").exists()

    def test_group_edit(self, django_app, groups, manager):
        managers, planners, volunteers = groups
        # promote planning group to management group, so we can delete the management group
        form = django_app.get(
            reverse("core:group_edit", kwargs={"pk": planners.id}), user=manager
        ).form
        form["is_management_group"] = True
        form.submit()

        form = django_app.get(
            reverse("core:group_edit", kwargs={"pk": managers.id}), user=manager
        ).form
        group_name = "New name"
        form["name"] = group_name
        form["users"].force_value([manager.id])
        form["is_planning_group"] = False
        form["is_management_group"] = False
        form["publish_event_for_group"].select_multiple(texts=["Volunteers"])
        response = form.submit()
        assert response.status_code == 302
        managers.refresh_from_db()
        assert managers.name == group_name
        assert set(managers.user_set.all()) == {manager}
        assert not managers.permissions.filter(codename="add_event").exists()
        assert "publish_event_for_group" not in get_group_perms(
            managers, Group.objects.get(name="Volunteers")
        )

    def test_group_delete(self, django_app, groups, manager):
        group = Group(name="Testgroup")
        group.save()
        response = django_app.get(
            reverse("core:group_delete", kwargs={"pk": group.id}), user=manager
        )
        assert response.status_code == 200
        response = response.form.submit()
        assert response.status_code == 302
        with pytest.raises(Group.DoesNotExist):
            Group.objects.get(name=group.name).exists()

    def test_cannot_delete_last_management_group(self, django_app, groups, manager):
        group = Group.objects.get(name="Managers")
        response = django_app.get(
            reverse("core:group_delete", kwargs={"pk": group.id}),
            user=manager,
            status=200,
        )
        response = response.form.submit()
        assert response.status_code == 200
        assert "least one group with management permissions" in response.text
        assert Group.objects.filter(name="Managers").exists()

    def test_management_perms_cannot_be_removed_from_last_management_group(
        self, django_app, superuser, groups
    ):
        group = Group.objects.get(name="Managers")
        form = django_app.get(
            reverse("core:group_edit", kwargs={"pk": group.id}),
            user=superuser,
            status=200,
        ).form
        form["is_management_group"] = False
        response = form.submit()
        assert response.status_code == 200
        assert "least one group with management permissions must exist" in response.text
        assert Group.objects.get(name="Managers") in get_groups_with_perms(
            only_with_perms_in=MANAGEMENT_PERMISSIONS, must_have_all_perms=True
        )
