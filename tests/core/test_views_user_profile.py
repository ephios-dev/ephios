import re

import pytest
from django.urls import reverse
from django.utils.formats import date_format


@pytest.mark.django_db
class TestUserProfileView:
    def test_no_permission_required(self, django_app, volunteer):
        response = django_app.get(reverse("core:profile"), user=volunteer)
        assert response.status_code == 200

    def test_correct_user_data_displayed(
        self, django_app, superuser, manager, planner, volunteer, responsible_user
    ):
        users = [superuser, manager, planner, volunteer, responsible_user]
        for user in users:
            response = django_app.get(reverse("core:profile"), user=user)
            assert response.html.find("dd", text=user.first_name)
            assert response.html.find("dd", text=user.last_name)
            assert response.html.find("dd", text=user.email)
            assert response.html.find(
                "dd", text=date_format(user.date_of_birth, format="DATE_FORMAT")
            )
            assert response.html.find("dd", text=user.phone)

    def test_correct_qualifications(self, django_app, qualified_volunteer):
        response = django_app.get(reverse("core:profile"), user=qualified_volunteer)
        for q in qualified_volunteer.qualifications:
            if q.expires is not None:
                assert True
            else:
                assert response.html.findAll("li", text=re.compile(f"{q.title}"))
