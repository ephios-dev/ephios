from datetime import datetime

import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp
from guardian.shortcuts import assign_perm
from webtest import TestApp

from user_management.models import UserProfile


@pytest.mark.django_db
class TestGroupView:
    def test_group_list_permission_required(self, django_app, volunteer_user):
        response = django_app.get(reverse("user_management:group_list"), user=volunteer_user)
        assert response.status_code == 302

    def test_group_list(self, django_app: DjangoTestApp, manager_user):
        response = django_app.get(reverse("user_management:group_list"), user=manager_user)
        assert response.status_code == 200
        assert response.html.findAll(text="Managers")
