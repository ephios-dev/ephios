import logging
import uuid
from argparse import Namespace
from datetime import date, datetime

import pytest
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.utils.timezone import get_default_timezone
from dynamic_preferences.registries import global_preferences_registry
from guardian.shortcuts import assign_perm

from ephios.core import plugins
from ephios.core.consequences import QualificationConsequenceHandler, WorkingHoursConsequenceHandler
from ephios.core.forms.users import MANAGEMENT_PERMISSIONS
from ephios.core.models import (
    AbstractParticipation,
    Event,
    EventType,
    LocalParticipation,
    Qualification,
    QualificationCategory,
    QualificationGrant,
    Shift,
    UserProfile,
    WorkingHours,
)
from ephios.core.models.users import IdentityProvider
from ephios.plugins.baseshiftstructures.structure.uniform import UniformShiftStructure
from ephios.plugins.basesignupflows.flow.participant import RequestConfirmSignupFlow


@pytest.fixture(autouse=True)
def check_log_for_exceptions(caplog):
    caplog.set_level(logging.ERROR)
    yield
    assert caplog.get_records("call") == []


@pytest.fixture(autouse=True)
def clear_cache():
    # The cache is not cleared after a test, but we need it to be for test isolation
    # because e.g. dynamic preferences uses the cache
    yield
    cache.clear()


@pytest.fixture
def csrf_exempt_django_app(django_app_factory):
    return django_app_factory(csrf_checks=False)


def pytest_collection_modifyitems(items):
    # mark all tests for use with django_db, as we basically need it everywhere
    for item in items:
        item.add_marker("django_db")


@pytest.fixture(autouse=True)
def enable_plugins():
    preferences = global_preferences_registry.manager()
    preferences["general__enabled_plugins"] = [
        plugin.module for plugin in plugins.get_all_plugins() if getattr(plugin, "visible", True)
    ]


@pytest.fixture
def tz():
    return get_default_timezone()


@pytest.fixture
def superuser():
    return UserProfile.objects.create(
        display_name="Rica Boss",
        is_staff=True,
        is_superuser=True,
        email="rica@localhost",
        date_of_birth=date(1970, 1, 1),
        password="dummy",
    )


@pytest.fixture
def manager():
    return UserProfile.objects.create(
        display_name="Marie Hilfsboss",
        email="marie@localhost",
        date_of_birth=date(1975, 1, 1),
        password="dummy",
    )


@pytest.fixture
def planner():
    return UserProfile.objects.create(
        display_name="Luisa Durchblick",
        email="luisa@localhost",
        date_of_birth=date(1980, 1, 1),
        password="dummy",
    )


@pytest.fixture
def volunteer():
    return UserProfile.objects.create(
        display_name="Heinrich Helper",
        email="heinrich@localhost",
        date_of_birth=date(1990, 1, 1),
        password="dummy",
    )


@pytest.fixture
def qualified_volunteer(qualifications, tz):
    volunteer = UserProfile.objects.create(
        display_name="Marianne Medizinfrau",
        email="marianne@localhost",
        date_of_birth=date(1985, 1, 1),
        password="dummy",
    )
    QualificationGrant.objects.create(
        user=volunteer, qualification=qualifications.nfs, expires=datetime(2064, 4, 1, tzinfo=tz)
    )
    QualificationGrant.objects.create(
        user=volunteer, qualification=qualifications.c, expires=datetime(2090, 4, 1, tzinfo=tz)
    )
    QualificationGrant.objects.create(user=volunteer, qualification=qualifications.b, expires=None)
    return volunteer


@pytest.fixture
def responsible_user():
    return UserProfile.objects.create(
        display_name="Hildegart Helper",
        email="hildegart@localhost",
        date_of_birth=date(1960, 1, 1),
        password="dummy",
    )


@pytest.fixture
def service_event_type():
    return EventType.objects.create(title="Service", default_description="Food will be provided.")


@pytest.fixture
def training_event_type():
    return EventType.objects.create(title="Training")


@pytest.fixture
def groups(superuser, manager, planner, volunteer, qualified_volunteer):
    managers = Group.objects.create(name="Managers")
    planners = Group.objects.create(name="Planners")
    volunteers = Group.objects.create(name="Volunteers")

    managers.user_set.add(superuser)
    managers.user_set.add(manager)
    planners.user_set.add(superuser, planner)
    volunteers.user_set.add(planner, volunteer, qualified_volunteer)

    assign_perm("publish_event_for_group", planners, volunteers)
    assign_perm("core.add_event", planners)
    assign_perm("core.delete_event", planners)
    for perm in MANAGEMENT_PERMISSIONS:
        assign_perm(perm, managers)
    assign_perm("decide_workinghours_for_group", managers, volunteers)
    return managers, planners, volunteers


@pytest.fixture
def hr_group(volunteer):
    hr_group = Group.objects.create(name="HR")
    assign_perm("core.view_userprofile", hr_group)
    assign_perm("core.add_userprofile", hr_group)
    assign_perm("core.change_userprofile", hr_group)
    assign_perm("core.delete_userprofile", hr_group)
    hr_group.user_set.add(volunteer)
    return hr_group


@pytest.fixture
def event(groups, service_event_type, planner, tz):
    managers, planners, volunteers = groups

    event = Event.objects.create(
        title="Fission Festival",
        description="Rave and rescue!",
        location="Lärz",
        type=service_event_type,
        active=True,
    )
    assign_perm("view_event", [volunteers, planners], event)
    assign_perm("change_event", planners, event)

    Shift.objects.create(
        event=event,
        meeting_time=datetime(2099, 6, 30, 7, 0, tzinfo=tz),
        start_time=datetime(2099, 6, 30, 8, 0, tzinfo=tz),
        end_time=datetime(2099, 6, 30, 20, 30, tzinfo=tz),
        signup_flow_slug=RequestConfirmSignupFlow.slug,
        signup_flow_configuration=dict(user_can_decline_confirmed=True),
        structure_slug=UniformShiftStructure.slug,
        structure_configuration=dict(
            minimum_number_of_participants=0, maximum_number_of_participants=1
        ),
    )
    return event


@pytest.fixture
def conflicting_event(event, training_event_type, volunteer, groups):
    managers, planners, volunteers = groups
    conflicting_event = Event.objects.create(
        title="Conflicting event",
        description="clashes",
        location="Berlin",
        type=training_event_type,
        active=True,
    )

    assign_perm("view_event", [volunteers, planners], conflicting_event)
    assign_perm("change_event", planners, conflicting_event)

    Shift.objects.create(
        event=conflicting_event,
        meeting_time=event.shifts.first().meeting_time,
        start_time=event.shifts.first().start_time,
        end_time=event.shifts.first().end_time,
        signup_flow_slug=RequestConfirmSignupFlow.slug,
        structure_slug=UniformShiftStructure.slug,
        signup_flow_configuration={},
        structure_configuration={},
    )

    LocalParticipation.objects.create(
        shift=conflicting_event.shifts.first(),
        user=volunteer,
        state=AbstractParticipation.States.CONFIRMED,
    )

    return conflicting_event


@pytest.fixture
def event_with_required_qualification(event, qualifications):
    shift = event.shifts.first()
    shift.structure_configuration = {"required_qualification_ids": [qualifications.nfs.pk]}
    shift.save()
    return event


@pytest.fixture
def event_to_next_day(groups, service_event_type, planner, tz):
    managers, planners, volunteers = groups

    event = Event.objects.create(
        title="Party until next day",
        description="all night long",
        location="Potsdam",
        type=service_event_type,
        active=True,
    )
    assign_perm("view_event", [volunteers, planners], event)
    assign_perm("change_event", planners, event)

    Shift.objects.create(
        event=event,
        meeting_time=datetime(2099, 6, 30, 18, 0, tzinfo=tz),
        start_time=datetime(2099, 6, 30, 19, 0, tzinfo=tz),
        end_time=datetime(2099, 7, 1, 6, 0, tzinfo=tz),
        signup_flow_slug=RequestConfirmSignupFlow.slug,
        signup_flow_configuration=dict(user_can_decline_confirmed=True),
        structure_slug=UniformShiftStructure.slug,
        structure_configuration=dict(),
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
        active=True,
    )
    assign_perm("view_event", [volunteers, planners], event)
    assign_perm("change_event", planners, event)

    Shift.objects.create(
        event=event,
        meeting_time=datetime(2099, 6, 30, 7, 0, tzinfo=tz),
        start_time=datetime(2099, 6, 30, 8, 0, tzinfo=tz),
        end_time=datetime(2099, 6, 30, 20, 0, tzinfo=tz),
        signup_flow_slug=RequestConfirmSignupFlow.slug,
        signup_flow_configuration=dict(user_can_decline_confirmed=True),
        structure_slug=UniformShiftStructure.slug,
        structure_configuration=dict(),
    )

    Shift.objects.create(
        event=event,
        meeting_time=datetime(2099, 7, 1, 7, 0, tzinfo=tz),
        start_time=datetime(2099, 7, 1, 8, 0, tzinfo=tz),
        end_time=datetime(2099, 7, 1, 20, 0, tzinfo=tz),
        signup_flow_slug=RequestConfirmSignupFlow.slug,
        signup_flow_configuration=dict(user_can_decline_confirmed=True),
        structure_slug=UniformShiftStructure.slug,
        structure_configuration=dict(),
    )
    return event


@pytest.fixture
def qualifications():
    """
    Some medical qualifications, returned as a namespace.
    """
    q = Namespace()
    medical_category = QualificationCategory.objects.create(
        title="Medical", uuid=uuid.UUID("50380292-b9c9-4711-b70d-8e03e2784cfb")
    )

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
    q.nfs.includes.add(q.rs)
    q.na = Qualification.objects.create(
        category=medical_category,
        title="Notarzt",
        abbreviation="NA",
        uuid=uuid.UUID("cb4f4ebc-3adf-4d32-a427-0ac0f686038a"),
    )

    driverslicense_category = QualificationCategory.objects.create(
        title="License", uuid=uuid.UUID("a5669cc2-7444-4046-8c33-d8ee0bbf881b")
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
    q.be.includes.add(q.b)
    q.c1 = Qualification.objects.create(
        category=driverslicense_category,
        title="Fahrerlaubnis Klasse C1",
        abbreviation="Fe C1",
        uuid=uuid.UUID("c9898e6c-4ecf-4781-9c0a-884861e36a81"),
    )
    q.c1.includes.add(q.b)
    q.c = Qualification.objects.create(
        category=driverslicense_category,
        title="Fahrerlaubnis Klasse C",
        abbreviation="Fe C",
        uuid=uuid.UUID("2d2fc932-5206-4c2c-bb63-0bc579acea6f"),
    )
    q.c.includes.add(q.c1)
    q.c1e = Qualification.objects.create(
        category=driverslicense_category,
        title="Fahrerlaubnis Klasse C1E",
        abbreviation="Fe C1E",
        uuid=uuid.UUID("f5e3be89-59de-4b13-a92f-5949009f62d8"),
    )
    q.c1e.includes.add(q.c1)
    q.c1e.includes.add(q.be)
    q.ce = Qualification.objects.create(
        category=driverslicense_category,
        title="Fahrerlaubnis Klasse CE",
        abbreviation="Fe CE",
        uuid=uuid.UUID("736ca05a-7ff9-423a-9fa4-8b4641fde29c"),
    )
    q.ce.includes.add(q.c)
    q.ce.includes.add(q.c1e)

    return q


@pytest.fixture
def qualifications_consequence(volunteer, qualifications, event, tz):
    return QualificationConsequenceHandler.create(
        user=volunteer,
        shift=event.shifts.first(),
        qualification=qualifications.nfs,
        expires=datetime(2065, 4, 1, tzinfo=tz),
    )


@pytest.fixture
def workinghours_consequence(volunteer):
    return WorkingHoursConsequenceHandler.create(
        user=volunteer, when=date(2020, 1, 1), hours=42, reason="testing"
    )


@pytest.fixture
def workinghours(volunteer):
    today = datetime.today()
    return [
        WorkingHours.objects.create(
            user=volunteer, hours=21, reason="Lager aufräumen", date=date(today.year - 1, 1, 1)
        ),
        WorkingHours.objects.create(
            user=volunteer, hours=21, reason="RTW checken", date=date(today.year, 1, 1)
        ),
    ]


@pytest.fixture
def oidc_client():
    return IdentityProvider.objects.create(
        label="Test Client",
        client_id="test_client",
        client_secret="test_secret",
        scopes="openid profile email",
        authorization_endpoint="https://example.com/auth",
        token_endpoint="https://example.com/token",
        jwks_uri="https://example.com/jwks",
        userinfo_endpoint="https://example.com/userinfo",
    )
