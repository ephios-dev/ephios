import itertools

from django.urls import reverse

from ephios.modellogging.log import add_log_recorder
from ephios.modellogging.models import LogEntry
from ephios.modellogging.recorders import FixedMessageLogRecorder


def test_log_view(django_app, event, superuser):
    response = django_app.get(reverse("core:log"), user=superuser, status=200)
    assert response
    assert event.title in response
    assert LogEntry.objects.count() > 5  # lots of entries for the fixtures


def test_log_for_event(django_app, event, superuser):
    response = django_app.get(event.get_absolute_url(), user=superuser, status=200).click(
        "View edit history"
    )
    assert response
    for logentry in response.context["logentry_list"]:
        assert logentry.attached_to_object == event


def test_fixed_log_message(django_app, event, superuser):
    # need show_value_statement as the fixuture is still holding the creation logentry
    add_log_recorder(
        event,
        FixedMessageLogRecorder(label="Test", message="a fixed message", show_value_statement=True),
    )
    event.save()
    response = django_app.get(event.get_absolute_url(), user=superuser, status=200).click(
        "View edit history"
    )
    assert "a fixed message" in response


def test_event_permission_changes_get_logged(django_app, event, superuser, qualified_volunteer):
    event_form = django_app.get(
        reverse("core:event_edit", kwargs=dict(pk=event.pk)),
        user=superuser,
    ).form
    event_form["responsible_users"].force_value([qualified_volunteer.id])
    pre_count = LogEntry.objects.count()
    response = event_form.submit().follow().click("View edit history")
    assert f"Responsibles added: {str(qualified_volunteer)}" in response
    new_count = LogEntry.objects.count() - pre_count
    assert any(  # there is any new entry with a record for the added user
        any(
            getattr(record, "added", None) == [str(qualified_volunteer)] for record in entry.records
        )
        for entry in LogEntry.objects.all()[:new_count]
    )


def test_group_logging(django_app, superuser, groups, qualified_volunteer):
    pre_count = LogEntry.objects.count()
    __, planners, __ = groups
    form = django_app.get(
        reverse("core:group_edit", kwargs={"pk": planners.id}), user=superuser
    ).form
    form["users"].force_value([qualified_volunteer.id])
    form["is_planning_group"] = False
    users_before = list(planners.user_set.all())
    assert form.submit()
    assert LogEntry.objects.count() == pre_count + 1
    response = django_app.get(
        f"{reverse('core:log')}?object_type=group&object_id={planners.id}", user=superuser
    )
    assert f"Users added: {qualified_volunteer}" in response
    assert any(
        f"Users removed: {str(user_a)}, {str(user_b)}" in response
        for user_a, user_b in itertools.permutations(users_before)
    )
    assert "Can add events: yes → no" in response


def test_user_cant_access_log(django_app, qualified_volunteer):
    django_app.get(reverse("core:log"), user=qualified_volunteer, status=403)


def test_managers_can_access_log(django_app, manager, groups):
    django_app.get(reverse("core:log"), user=manager, status=200)
