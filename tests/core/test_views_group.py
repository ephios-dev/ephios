import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from guardian.shortcuts import get_group_perms, get_objects_for_group


@pytest.mark.django_db
class TestGroupView:
    def test_group_list_permission_required(self, django_app, volunteer):
        response = django_app.get(reverse("core:group_list"), user=volunteer, status=403)
        assert response.status_code == 403

    def test_group_list(self, django_app, superuser, groups):
        response = django_app.get(reverse("core:group_list"), user=superuser)
        assert response.status_code == 200
        assert response.html.findAll(text=Group.objects.all().values_list("name", flat=True))
        edit_links = [
            reverse("core:group_edit", kwargs={"pk": group_id})
            for group_id in Group.objects.all().values_list("id", flat=True)
        ]
        assert response.html.findAll("a", href=edit_links)

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
        assert not group.permissions.filter(codename="view_past_event").exists()
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
        form["can_view_past_event"] = True
        form["is_planning_group"] = True
        form["publish_event_for_group"].select_multiple(texts=["Volunteers"])
        form["is_hr_group"] = True
        form["is_management_group"] = True
        response = form.submit()
        assert response.status_code == 302
        group = Group.objects.get(name=group_name)
        assert set(group.user_set.all()) == {manager}
        assert group.permissions.filter(codename="view_past_event").exists()
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
        group = manager.groups.first()
        form = django_app.get(
            reverse("core:group_edit", kwargs={"pk": group.id}), user=manager
        ).form
        group_name = "New name"
        form["name"] = group_name
        form["users"].force_value([manager.id])
        form["can_view_past_event"] = False
        form["is_planning_group"] = False
        form["is_management_group"] = False
        form["publish_event_for_group"].select_multiple(texts=["Volunteers"])
        response = form.submit()
        assert response.status_code == 302
        group.refresh_from_db()
        assert group.name == group_name
        assert set(group.user_set.all()) == {manager}
        assert not group.permissions.filter(codename="view_past_event").exists()
        assert not group.permissions.filter(codename="add_event").exists()
        assert "publish_event_for_group" not in get_group_perms(
            group, Group.objects.get(name="Volunteers")
        )

    def test_publish_for_groups_gets_saved_for_non_planner_groups(
        self, django_app, groups, manager
    ):
        managers, planners, volunteers = groups
        form = django_app.get(
            reverse("core:group_edit", kwargs={"pk": managers.id}), user=manager
        ).form
        form["users"].force_value([manager.id])
        form["is_planning_group"] = False
        form["is_management_group"] = True
        form["is_hr_group"] = False
        form["publish_event_for_group"].select_multiple(texts=["Volunteers"])
        form.submit().follow()
        managers.refresh_from_db()
        assert set(get_objects_for_group(managers, ["publish_event_for_group"], klass=Group)) == {
            volunteers
        }

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
