from datetime import datetime

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from django_webtest import DjangoTestApp
from guardian.shortcuts import assign_perm
from webtest import TestApp

from user_management.models import UserProfile


@pytest.mark.django_db
class TestGroupView:
    def test_group_list_permission_required(self, django_app, volunteer_user):
        response = django_app.get(
            reverse("user_management:group_list"), user=volunteer_user, status=403
        )
        assert response.status_code == 403

    def test_group_list(self, django_app, manager_user):
        response = django_app.get(reverse("user_management:group_list"), user=manager_user)
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

    def test_group_create_permission_required(self, django_app, volunteer_user):
        response = django_app.get(
            reverse("user_management:group_add"), user=volunteer_user, status=403
        )
        assert response.status_code == 403

    # does not work because of select2 heavy widgets
    # def test_group_create_successful(self, django_app, manager_user):
    #     response = django_app.get(reverse("user_management:group_add"), user=manager_user)
    #     form = response.form
    #     group_name = "Testgroup"
    #     form["name"] = group_name
    #     form["users"].select_multiple(texts=[manager_user.get_full_name()])
    #     response = form.submit()
    #     assert response.status == 200
    #     group = Group.objects.get(name=group_name)
    #     assert group.name == group_name
    #     assert group.user_set == UserProfile.objects.filter(pk=manager_user.pk)
