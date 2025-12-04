from datetime import datetime

import pytest
from django.urls import reverse
from django.utils.timezone import make_aware
from dynamic_preferences.registries import global_preferences_registry
from guardian.shortcuts import assign_perm

from ephios.core.models import (
    AbstractParticipation,
    LocalParticipation,
    QualificationGrant,
)
from ephios.core.models.users import AbstractConsequence
from ephios.core.signals import periodic_signal
from ephios.plugins.eventautoqualification.models import EventAutoQualificationConfiguration


def test_planners_cant_edit_autoqualification(django_app, event, planner):
    preferences = global_preferences_registry.manager()
    preferences["general__enabled_plugins"] = [
        "ephios.plugins.baseshiftstructures",
        "ephios.plugins.basesignupflows",
        "ephios.plugins.eventautoqualification",
    ]

    assert (
        "disabled"
        in django_app.get(reverse("core:event_edit", kwargs=dict(pk=event.pk)), user=planner)
        .form["autoqualification-qualification"]
        .attrs
    )


def test_autoqualification_settings_flow(django_app, event, manager, qualifications):
    preferences = global_preferences_registry.manager()
    preferences["general__enabled_plugins"] = [
        "ephios.plugins.baseshiftstructures",
        "ephios.plugins.basesignupflows",
        "ephios.plugins.eventautoqualification",
    ]
    assign_perm("change_event", manager, event)
    event_update_view = django_app.get(
        reverse("core:event_edit", kwargs=dict(pk=event.pk)), user=manager
    )
    with pytest.raises(EventAutoQualificationConfiguration.DoesNotExist):
        event.auto_qualification_config
    assert "Automatic qualification" in event_update_view

    event_update_view.form["autoqualification-qualification"] = qualifications.na.id
    event_update_view.form.submit()

    event.refresh_from_db()
    assert event.auto_qualification_config.qualification == qualifications.na

    # remove it again
    event_update_view = django_app.get(
        reverse("core:event_edit", kwargs=dict(pk=event.pk)), user=manager
    )
    event_update_view.form["autoqualification-qualification"] = ""
    event_update_view.form.submit()

    assert not EventAutoQualificationConfiguration.objects.exists()


def test_overwrite_qualification_expiration_date(
    multi_shift_event, event, manager, qualifications, volunteer
):
    preferences = global_preferences_registry.manager()
    preferences["general__enabled_plugins"] = [
        "ephios.plugins.baseshiftstructures",
        "ephios.plugins.basesignupflows",
        "ephios.plugins.eventautoqualification",
    ]
    EventAutoQualificationConfiguration.objects.create(
        event=multi_shift_event,
        qualification=qualifications.na,
        mode=EventAutoQualificationConfiguration.Modes.ANY_SHIFT,
        expiration_date=None,
        needs_confirmation=False,
    )

    QualificationGrant.objects.create(
        user=volunteer, qualification=qualifications.na, expires=make_aware(datetime(2097, 6, 1))
    )
    for shift in multi_shift_event.shifts.all():
        shift.start_time = shift.start_time.replace(year=2020)
        shift.end_time = shift.end_time.replace(year=2020)
        shift.save()
        LocalParticipation.objects.create(
            user=volunteer, shift=shift, state=AbstractParticipation.States.CONFIRMED
        )

    periodic_signal.send(None)
    volunteer.refresh_from_db()
    assert volunteer.qualification_grants.get().expires is None


@pytest.mark.parametrize(
    "year,mode,signup_states,consequence_expected",
    [
        (
            2099,
            EventAutoQualificationConfiguration.Modes.ANY_SHIFT,
            [AbstractParticipation.States.REQUESTED, None],
            False,
        ),
        (
            2020,
            EventAutoQualificationConfiguration.Modes.ANY_SHIFT,
            [AbstractParticipation.States.REQUESTED, None],
            False,
        ),
        (
            2099,
            EventAutoQualificationConfiguration.Modes.ANY_SHIFT,
            [AbstractParticipation.States.CONFIRMED, None],
            False,
        ),
        (
            2020,
            EventAutoQualificationConfiguration.Modes.ANY_SHIFT,
            [AbstractParticipation.States.CONFIRMED, None],
            True,
        ),
        (
            2020,
            EventAutoQualificationConfiguration.Modes.LAST_SHIFT,
            [AbstractParticipation.States.CONFIRMED, None],
            False,
        ),
        (
            2020,
            EventAutoQualificationConfiguration.Modes.LAST_SHIFT,
            [None, AbstractParticipation.States.CONFIRMED],
            True,
        ),
        (
            2020,
            EventAutoQualificationConfiguration.Modes.EVERY_SHIFT,
            [None, AbstractParticipation.States.CONFIRMED],
            False,
        ),
        (
            2020,
            EventAutoQualificationConfiguration.Modes.EVERY_SHIFT,
            [AbstractParticipation.States.CONFIRMED, AbstractParticipation.States.CONFIRMED],
            True,
        ),
    ],
)
def test_consequence_gets_created(
    django_app,
    multi_shift_event,
    volunteer,
    qualifications,
    tz,
    year,
    mode,
    signup_states,
    consequence_expected,
):
    preferences = global_preferences_registry.manager()
    preferences["general__enabled_plugins"] = [
        "ephios.plugins.baseshiftstructures",
        "ephios.plugins.basesignupflows",
        "ephios.plugins.eventautoqualification",
    ]
    EventAutoQualificationConfiguration.objects.create(
        event=multi_shift_event, qualification=qualifications.na, mode=mode
    )
    for wanted_state, shift in zip(signup_states, multi_shift_event.shifts.all()):
        shift.start_time = shift.start_time.replace(year)
        shift.end_time = shift.end_time.replace(year)
        shift.save()
        if wanted_state:
            LocalParticipation.objects.create(user=volunteer, shift=shift, state=wanted_state)

    assert not AbstractConsequence.objects.exists()
    periodic_signal.send(None)

    if not consequence_expected:
        assert not AbstractConsequence.objects.exists()
    else:
        assert AbstractConsequence.objects.count() == 1
        periodic_signal.send(None)
        consequence = AbstractConsequence.objects.get()
        assert consequence.data["qualification_id"] == qualifications.na.id
        assert consequence.user == volunteer
