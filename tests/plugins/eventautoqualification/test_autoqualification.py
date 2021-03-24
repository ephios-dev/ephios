from datetime import datetime

import pytest
from django.urls import reverse
from dynamic_preferences.registries import global_preferences_registry
from guardian.shortcuts import assign_perm

from ephios.core.models import AbstractParticipation, Consequence, LocalParticipation
from ephios.core.signals import periodic_signal
from ephios.plugins.eventautoqualification.models import EventAutoQualificationConfiguration


@pytest.mark.django_db
def test_planners_cant_edit_autoqualification(django_app, event, planner):
    preferences = global_preferences_registry.manager()
    preferences["general__enabled_plugins"] = [
        "ephios.plugins.basesignup",
        "ephios.plugins.eventautoqualification",
    ]

    assert "Automatic qualification" not in django_app.get(
        reverse("core:event_edit", kwargs=dict(pk=event.pk)), user=planner
    )


@pytest.mark.django_db
def test_autoqualification_settings_flow(django_app, event, manager, qualifications):
    preferences = global_preferences_registry.manager()
    preferences["general__enabled_plugins"] = [
        "ephios.plugins.basesignup",
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


@pytest.mark.django_db
@pytest.mark.parametrize(
    "year,state,mode,consequence_expected",
    [
        (
            2099,
            AbstractParticipation.States.REQUESTED,
            EventAutoQualificationConfiguration.Modes.ANY_SHIFT,
            False,
        ),
        (
            2020,
            AbstractParticipation.States.REQUESTED,
            EventAutoQualificationConfiguration.Modes.ANY_SHIFT,
            False,
        ),
        (
            2099,
            AbstractParticipation.States.CONFIRMED,
            EventAutoQualificationConfiguration.Modes.ANY_SHIFT,
            False,
        ),
        (
            2020,
            AbstractParticipation.States.CONFIRMED,
            EventAutoQualificationConfiguration.Modes.ANY_SHIFT,
            True,
        ),
        (
            2020,
            AbstractParticipation.States.CONFIRMED,
            EventAutoQualificationConfiguration.Modes.LAST_SHIFT,
            False,
        ),
        (
            2020,
            AbstractParticipation.States.CONFIRMED,
            EventAutoQualificationConfiguration.Modes.EVERY_SHIFT,
            False,
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
    state,
    mode,
    consequence_expected,
):
    preferences = global_preferences_registry.manager()
    preferences["general__enabled_plugins"] = [
        "ephios.plugins.basesignup",
        "ephios.plugins.eventautoqualification",
    ]
    EventAutoQualificationConfiguration.objects.create(
        event=multi_shift_event, qualification=qualifications.na, mode=mode
    )
    shift = multi_shift_event.shifts.first()
    LocalParticipation.objects.create(user=volunteer, shift=shift, state=state)

    shift.start_time = datetime(year, 6, 30, 7, 0).astimezone(tz)
    shift.end_time = datetime(year, 6, 30, 15, 0).astimezone(tz)
    shift.save()

    assert not Consequence.objects.exists()
    periodic_signal.send(None)

    if not consequence_expected:
        assert not Consequence.objects.exists()
    else:
        assert Consequence.objects.count() == 1
        periodic_signal.send(None)
        assert Consequence.objects.count() == 1
        consequence = Consequence.objects.get()
        assert consequence.data["qualification_id"] == qualifications.na.id
        assert consequence.user == volunteer
