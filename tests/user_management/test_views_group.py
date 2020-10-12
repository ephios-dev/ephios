import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from pytest_django.asserts import assertQuerysetEqual


@pytest.mark.django_db
class TestGroupView:
    def test_group_list_permission_required(self, django_app, volunteer):
        response = django_app.get(reverse("user_management:group_list"), user=volunteer, status=403)
        assert response.status_code == 403

    def test_group_list(self, django_app, superuser, groups):
        response = django_app.get(reverse("user_management:group_list"), user=superuser)
        assert response.status_code == 200
        assert response.html.findAll(text="Managers")

    # def test_group_edit_button(self, django_app, manager_user):
    #     response = django_app.get(reverse("user_management:group_list"), user=manager_user)
    #     response.showbrowser()
    #     target_response = response.clickbutton(description="Bearbeiten", verbose=True)
    #     assertRedirects(
    #         target_response,
    #         reverse("user_management:group_edit", kwargs={"pk": manager_user.groups.first().pk})
    #     )

    def test_group_create_permission_required(self, django_app, volunteer):
        response = django_app.get(reverse("user_management:group_add"), user=volunteer, status=403)
        assert response.status_code == 403

    def test_group_create_successful(self, django_app, superuser):
        response = django_app.get(reverse("user_management:group_add"), user=superuser)
        form = response.form
        group_name = "Testgroup"
        form["name"] = group_name
        form["users"].force_value([superuser.id])
        response = form.submit()
        assert response.status_code == 302
        group = Group.objects.get(name=group_name)
        assert group.name == group_name
        assertQuerysetEqual(group.user_set.all(), [superuser])
