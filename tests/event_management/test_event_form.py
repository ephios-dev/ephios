from datetime import date, time

import pytest
from django.urls import reverse
from guardian.shortcuts import get_users_with_perms

from ephios.extra.permissions import get_groups_with_perms


@pytest.mark.django_db
def test_create_event(django_app, planner, superuser, service_event_type, groups):
    managers, planners, volunteers = groups

    event_form = django_app.get(
        reverse("event_management:event_create", kwargs=dict(type=service_event_type.pk)),
        user=planner,
    ).form
    event_form["title"] = "Seeed Concert"
    event_form["description"] = "when at location, call 0123456789"
    event_form["location"] = "BOS ARENA"
    event_form["mail_updates"] = True
    event_form["visible_for"] = [volunteers.id]
    event_form["responsible_groups"] = [planners.id]
    # event_form["responsible_users"] is prefilled with planner
    shift_form = event_form.submit().follow().form
    shift_form["date"] = date.today()
    shift_form["meeting_time"] = time(9, 0)
    shift_form["start_time"] = time(10, 0)
    shift_form["end_time"] = time(16, 0)
    event = shift_form.submit().follow().context["event"]
    assert event.title == "Seeed Concert"
    assert set(get_groups_with_perms(event, only_with_perms_in=["view_event"])) == {
        volunteers,
        planners,
    }
    assert set(get_groups_with_perms(event, only_with_perms_in=["change_event"])) == {planners}
    assert set(
        get_users_with_perms(event, only_with_perms_in=["change_event"], with_group_users=False)
    ) == {planner}
    assert set(get_users_with_perms(event, only_with_perms_in=["change_event"])) == {
        planner,
        superuser,
    }  # superuser is in planner group


@pytest.mark.django_db
def test_add_responsible_user_to_event(django_app, planner, event, responsible_user):
    response = django_app.get(
        reverse("event_management:event_edit", kwargs=dict(pk=event.pk)), user=planner
    )
    # select2 selects must be forced as they don't have html options
    response.form["responsible_users"].force_value([responsible_user.id])
    event = response.form.submit().follow().context["event"]
    assert set(
        get_users_with_perms(event, only_with_perms_in=["change_event"], with_group_users=False)
    ) == {responsible_user}
