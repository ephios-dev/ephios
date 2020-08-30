from datetime import datetime

import pytest
from django.contrib.auth.models import Group
from guardian.shortcuts import assign_perm

from user_management.models import UserProfile


@pytest.fixture
def volunteer_user(db):
    volunteer_group = Group.objects.create(name="Volunteers")
    user = UserProfile.objects.create(
        email="volunteer@test",
        first_name="Volunteer",
        last_name="User",
        date_of_birth=datetime.now(),
    )
    user.groups.add(volunteer_group)
    return user


@pytest.fixture
def planner_user(db, volunteer_user):
    planner_group = Group.objects.create(name="Planner")
    user = UserProfile.objects.create(
        email="planner@test", first_name="Planner", last_name="User", date_of_birth=datetime.now()
    )
    user.groups.add(planner_group)
    assign_perm("publish_event_for_group", planner_group, volunteer_user.groups.first())
    assign_perm("event_management.add_event", planner_group)
    assign_perm("event_management.delete_event", planner_group)
    return user


@pytest.fixture
def manager_user(db):
    manager_group = Group.objects.create(name="Managers")
    user = UserProfile.objects.create(
        email="manager@test", first_name="Manager", last_name="User", date_of_birth=datetime.now()
    )
    user.groups.add(manager_group)
    assign_perm("user_management.view_userprofile", manager_group)
    assign_perm("user_management.add_userprofile", manager_group)
    assign_perm("user_management.change_userprofile", manager_group)
    assign_perm("user_management.delete_userprofile", manager_group)
    assign_perm("auth.view_group", manager_group)
    assign_perm("auth.add_group", manager_group)
    assign_perm("auth.change_group", manager_group)
    assign_perm("auth.delete_group", manager_group)
    return user
