from datetime import date, time

from django.contrib.auth.models import Group
from django.urls import reverse
from guardian.shortcuts import get_objects_for_user, get_users_with_perms

from ephios.core.models import AbstractParticipation, LocalParticipation
from ephios.extra.permissions import get_groups_with_perms


def test_create_event(django_app, planner, superuser, service_event_type, groups):
    managers, planners, volunteers = groups

    event_form = django_app.get(
        reverse("core:event_create", kwargs=dict(type=service_event_type.pk)),
        user=planner,
    ).form
    event_form["title"] = "Seeed Concert"
    event_form["location"] = "BOS ARENA"
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
    assert event.description == "Food will be provided."
    assert event.type == service_event_type
    assert set(get_groups_with_perms(event, only_with_perms_in=["view_event"])) == {
        volunteers,
        planners,
        managers,
    }
    assert set(get_groups_with_perms(event, only_with_perms_in=["change_event"])) == {
        planners,
        managers,
    }
    assert set(
        get_users_with_perms(event, only_with_perms_in=["change_event"], with_group_users=False)
    ) == {planner}
    assert set(get_users_with_perms(event, only_with_perms_in=["change_event"])) == {
        planner,
        superuser,
    }  # superuser is in planner group


def test_create_form_error(django_app, planner, superuser, service_event_type, groups):
    managers, planners, volunteers = groups

    event_form = django_app.get(
        reverse("core:event_create", kwargs=dict(type=service_event_type.pk)),
        user=planner,
    ).form
    event_form["title"] = "Seeed Concert"
    event_form["location"] = "BOS ARENA"
    event_form["visible_for"].force_value([
        volunteers.id,
        999,
    ])  # invalid ID! (perhaps the group was deleted meanwhile)
    response = event_form.submit()
    assert "999 is not one of the available choices." in response.text


def test_edit_event_with_participating_responsible(
    django_app, planner, qualified_volunteer, event, groups
):
    LocalParticipation.objects.create(
        shift=event.shifts.first(),
        user=qualified_volunteer,
        state=AbstractParticipation.States.CONFIRMED,
    )
    event_form = django_app.get(
        reverse("core:event_edit", kwargs=dict(pk=event.pk)),
        user=planner,
    ).form
    event_form["responsible_users"].force_value([qualified_volunteer.id])
    event_form.submit()


def test_add_responsible_user_to_event(django_app, planner, event, responsible_user):
    response = django_app.get(reverse("core:event_edit", kwargs=dict(pk=event.pk)), user=planner)
    # select2 selects must be forced as they don't have html options
    response.form["responsible_users"].force_value([responsible_user.id])
    event = response.form.submit().follow().context["event"]
    assert set(
        get_users_with_perms(event, only_with_perms_in=["change_event"], with_group_users=False)
    ) == {responsible_user}


def test_participating_users_can_see_otherwise_invisible_event(
    django_app, planner, event, responsible_user, volunteer
):
    # create a participation
    LocalParticipation.objects.create(
        user=volunteer, shift=event.shifts.first(), state=LocalParticipation.States.CONFIRMED
    )
    assert list(event.shifts.first().get_participants())

    # make event invisible
    response = django_app.get(reverse("core:event_edit", kwargs=dict(pk=event.pk)), user=planner)
    response.form["visible_for"].force_value([])
    response.form.submit()

    # check that we can get (200 OK) the event details as a participant
    assert django_app.get(event.get_absolute_url(), user=volunteer)


def test_management_group_can_make_event_visible_for_all_groups(
    django_app, service_event_type, manager, groups
):
    event_form = django_app.get(
        reverse("core:event_create", kwargs=dict(type=service_event_type.pk)),
        user=manager,
    ).form
    num_groups = Group.objects.count()
    assert (
        get_objects_for_user(
            manager, "publish_event_for_group", klass=Group, accept_global_perms=False
        ).count()
        < num_groups
    )
    assert num_groups == len(event_form["visible_for"].options)


def test_unsaved_event_warning(django_app, planner, groups, service_event_type):
    event_form = django_app.get(
        reverse("core:event_create", kwargs=dict(type=service_event_type.pk)),
        user=planner,
    ).form
    event_form["title"] = "Seeed Concert"
    event_form["location"] = "BOS ARENA"
    event_form.submit()
    # we now have created an event but it has not been activated
    # we expect to get a notice about that when trying to create a new event
    response = django_app.get(
        reverse("core:event_create", kwargs=dict(type=service_event_type.pk)),
        user=planner,
    )
    assert "You have an unsaved event" in response
    response = response.click("View")
    assert "This event has not been saved"
    assert not response.context["event"].active


def test_change_event_type(django_app, planner, event, service_event_type, training_event_type):
    assert event.type == service_event_type
    event_form = django_app.get(
        reverse("core:event_edit", kwargs=dict(pk=event.pk)),
        user=planner,
    ).form
    event_form["type"] = training_event_type.pk
    event_form.submit()
    event.refresh_from_db()
    assert event.type == training_event_type
