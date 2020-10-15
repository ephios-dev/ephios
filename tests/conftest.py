from datetime import date, datetime

import pytest
from django.contrib.auth.models import Group
from guardian.shortcuts import assign_perm

from ephios.event_management.models import EventType, Event, Shift
from ephios.plugins.basesignup.signup.confirm import RequestConfirmSignupMethod
from ephios.user_management.models import UserProfile


@pytest.fixture
def superuser():
    return UserProfile.objects.create(
        first_name="Rica",
        last_name="Boss",
        is_staff=True,
        is_superuser=True,
        email="rica@localhost",
        date_of_birth=date(1970, 1, 1),
        password="dummy",
    )


@pytest.fixture
def manager():
    return UserProfile.objects.create(
        first_name="Marie",
        last_name="Hilfsboss",
        email="marie@localhost",
        date_of_birth=date(1975, 1, 1),
        password="dummy",
    )


@pytest.fixture
def planner():
    return UserProfile.objects.create(
        first_name="Luisa",
        last_name="Durchblick",
        email="luisa@localhost",
        date_of_birth=date(1980, 1, 1),
        password="dummy",
    )


@pytest.fixture
def volunteer():
    return UserProfile.objects.create(
        first_name="Heinrich",
        last_name="Helper",
        email="heinrich@localhost",
        date_of_birth=date(1990, 1, 1),
        password="dummy",
    )


@pytest.fixture
def responsible_user():
    return UserProfile.objects.create(
        first_name="Hildegart",
        last_name="Helper",
        email="hildegart@localhost",
        date_of_birth=date(1960, 1, 1),
        password="dummy",
    )


@pytest.fixture
def service_event_type():
    return EventType.objects.create(title="Service", can_grant_qualification=False)


@pytest.fixture
def groups(superuser, manager, planner, volunteer):
    managers = Group.objects.create(name="Managers")
    planners = Group.objects.create(name="Planners")
    volunteers = Group.objects.create(name="Volunteers")

    managers.user_set.add(superuser)
    managers.user_set.add(manager)
    planners.user_set.add(superuser, planner)
    volunteers.user_set.add(superuser, planner, volunteer)

    assign_perm("publish_event_for_group", planners, volunteers)
    assign_perm("event_management.add_event", planners)
    assign_perm("event_management.delete_event", planners)
    assign_perm("event_management.view_past_event", planners)
    assign_perm("user_management.view_userprofile", managers)
    assign_perm("user_management.add_userprofile", managers)
    assign_perm("user_management.change_userprofile", managers)
    assign_perm("user_management.delete_userprofile", managers)
    assign_perm("auth.view_group", managers)
    assign_perm("auth.add_group", managers)
    assign_perm("auth.change_group", managers)
    assign_perm("auth.delete_group", managers)
    return managers, planners, volunteers


@pytest.fixture
def event(groups, service_event_type, planner):
    managers, planners, volunteers = groups

    event = Event.objects.create(
        title="Fission Festival",
        description="Rave and rescue!",
        location="Lärz",
        type=service_event_type,
        mail_updates=True,
        active=True,
    )
    assign_perm("view_event", [volunteers, planners], event)
    assign_perm("change_event", planners, event)

    Shift.objects.create(
        event=event,
        meeting_time=datetime(2099, 6, 30, 7, 0),
        start_time=datetime(2099, 6, 30, 8, 0),
        end_time=datetime(2099, 6, 30, 20, 0),
        signup_method_slug=RequestConfirmSignupMethod.slug,
        signup_configuration={},
    )
    return event
