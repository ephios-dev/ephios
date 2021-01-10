import uuid
from argparse import Namespace
from datetime import date, datetime

import pytest
import pytz
from django.contrib.auth.models import Group
from guardian.shortcuts import assign_perm

from ephios.event_management.models import Event, EventType, Shift
from ephios.plugins.basesignup.signup.simple import RequestConfirmSignupMethod
from ephios.user_management.consequences import (
    QualificationConsequenceHandler,
    WorkingHoursConsequenceHandler,
)
from ephios.user_management.models import (
    Qualification,
    QualificationCategory,
    UserProfile,
    WorkingHours,
)


@pytest.fixture
def tz():
    return pytz.timezone("Europe/Berlin")


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
def event(groups, service_event_type, planner, tz):
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
        meeting_time=datetime(2099, 6, 30, 7, 0).astimezone(tz),
        start_time=datetime(2099, 6, 30, 8, 0).astimezone(tz),
        end_time=datetime(2099, 6, 30, 20, 0).astimezone(tz),
        signup_method_slug=RequestConfirmSignupMethod.slug,
        signup_configuration={},
    )
    return event


@pytest.fixture
def event_to_next_day(groups, service_event_type, planner, tz):
    managers, planners, volunteers = groups

    event = Event.objects.create(
        title="Party until next day",
        description="all night long",
        location="Potsdam",
        type=service_event_type,
        mail_updates=True,
        active=True,
    )
    assign_perm("view_event", [volunteers, planners], event)
    assign_perm("change_event", planners, event)

    Shift.objects.create(
        event=event,
        meeting_time=datetime(2099, 6, 30, 18, 0).astimezone(tz),
        start_time=datetime(2099, 6, 30, 19, 0).astimezone(tz),
        end_time=datetime(2099, 7, 1, 6, 0).astimezone(tz),
        signup_method_slug=RequestConfirmSignupMethod.slug,
        signup_configuration={},
    )
    return event


@pytest.fixture
def multi_shift_event(groups, service_event_type, planner, tz):
    managers, planners, volunteers = groups

    event = Event.objects.create(
        title="Multi-shift event",
        description="long",
        location="Berlin",
        type=service_event_type,
        mail_updates=True,
        active=True,
    )
    assign_perm("view_event", [volunteers, planners], event)
    assign_perm("change_event", planners, event)

    Shift.objects.create(
        event=event,
        meeting_time=datetime(2099, 6, 30, 7, 0).astimezone(tz),
        start_time=datetime(2099, 6, 30, 8, 0).astimezone(tz),
        end_time=datetime(2099, 6, 30, 20, 0).astimezone(tz),
        signup_method_slug=RequestConfirmSignupMethod.slug,
        signup_configuration={},
    )

    Shift.objects.create(
        event=event,
        meeting_time=datetime(2099, 7, 1, 7, 0).astimezone(tz),
        start_time=datetime(2099, 7, 1, 8, 0).astimezone(tz),
        end_time=datetime(2099, 7, 1, 20, 0).astimezone(tz),
        signup_method_slug=RequestConfirmSignupMethod.slug,
        signup_configuration={},
    )
    return event


@pytest.fixture
def qualifications():
    """
    Subset of the qualifications of the setupdata fixture, returned as a namespace.
    """

    medical_category = QualificationCategory.objects.create(
        title="Medical",
        uuid=uuid.UUID("50380292-b9c9-4711-b70d-8e03e2784cfb"),
    )

    q = Namespace()

    q.rs = Qualification.objects.create(
        category=medical_category,
        title="Rettungssanitäter",
        abbreviation="RS",
        uuid=uuid.UUID("0b41fac6-ca9e-4b8a-82c5-849412187351"),
    )

    q.nfs = Qualification.objects.create(
        category=medical_category,
        title="Notfallsanitäter",
        abbreviation="NFS",
        uuid=uuid.UUID("d114125b-7cf4-49e2-8908-f93e2f95dfb8"),
    )
    q.nfs.included_qualifications.add(q.rs)

    q.na = Qualification.objects.create(
        category=medical_category,
        title="Notarzt",
        abbreviation="NA",
        uuid=uuid.UUID("cb4f4ebc-3adf-4d32-a427-0ac0f686038a"),
    )

    driverslicense_category = QualificationCategory.objects.create(
        title="License",
        uuid=uuid.UUID("a5669cc2-7444-4046-8c33-d8ee0bbf881b"),
    )

    q.b = Qualification.objects.create(
        category=driverslicense_category,
        title="Fahrerlaubnis Klasse B",
        abbreviation="Fe B",
        uuid=uuid.UUID("0715b687-877a-4fed-bde0-5ea06b1043fc"),
    )

    q.be = Qualification.objects.create(
        category=driverslicense_category,
        title="Fahrerlaubnis Klasse BE",
        abbreviation="Fe BE",
        uuid=uuid.UUID("31529f69-09d7-44cc-84f6-19fbfd949faa"),
    )
    q.be.included_qualifications.add(q.b)

    q.c1 = Qualification.objects.create(
        category=driverslicense_category,
        title="Fahrerlaubnis Klasse C1",
        abbreviation="Fe C1",
        uuid=uuid.UUID("c9898e6c-4ecf-4781-9c0a-884861e36a81"),
    )
    q.c1.included_qualifications.add(q.b)

    q.c = Qualification.objects.create(
        category=driverslicense_category,
        title="Fahrerlaubnis Klasse C",
        abbreviation="Fe C",
        uuid=uuid.UUID("2d2fc932-5206-4c2c-bb63-0bc579acea6f"),
    )
    q.c.included_qualifications.add(q.c1)

    q.c1e = Qualification.objects.create(
        category=driverslicense_category,
        title="Fahrerlaubnis Klasse C1E",
        abbreviation="Fe C1E",
        uuid=uuid.UUID("f5e3be89-59de-4b13-a92f-5949009f62d8"),
    )
    q.c1e.included_qualifications.add(q.c1)
    q.c1e.included_qualifications.add(q.be)

    q.ce = Qualification.objects.create(
        category=driverslicense_category,
        title="Fahrerlaubnis Klasse CE",
        abbreviation="Fe CE",
        uuid=uuid.UUID("736ca05a-7ff9-423a-9fa4-8b4641fde29c"),
    )
    q.ce.included_qualifications.add(q.c)
    q.ce.included_qualifications.add(q.c1e)

    return q


@pytest.fixture
def qualifications_consequence(volunteer, qualifications, event, tz):
    return QualificationConsequenceHandler.create(
        user=volunteer,
        shift=event.shifts.first(),
        qualification=qualifications.nfs,
        expires=datetime(2064, 4, 1).astimezone(tz),
    )


@pytest.fixture
def workinghours_consequence(volunteer):
    return WorkingHoursConsequenceHandler.create(
        user=volunteer, when=date(2020, 1, 1), hours=42, reason="testing"
    )


@pytest.fixture
def workinghours(volunteer):
    return [
        WorkingHours.objects.create(
            user=volunteer, hours=21, reason="Lager aufräumen", date=date(2020, 1, 1)
        ),
        WorkingHours.objects.create(
            user=volunteer, hours=21, reason="RTW checken", date=date(2021, 1, 1)
        ),
    ]
