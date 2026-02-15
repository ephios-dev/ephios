from datetime import timedelta

from django.urls import reverse

from ephios.core.models import LocalParticipation


def test_event_list_200(django_app, planner, event):
    event_list = django_app.get(reverse("core:event_list"), user=planner)
    assert event.title in event_list


def test_unsaved_event_not_in_event_list(django_app, planner, event):
    event.active = False
    event.save()
    event_list = django_app.get(reverse("core:event_list"), user=planner)
    assert event.title not in event_list


def test_list_view_mode_change_works(django_app, volunteer, event):
    response = django_app.get(reverse("core:event_list"), user=volunteer)
    assert "calendar" not in response.context and response.context["mode"] == "list"
    response = response.click("fa-calendar-alt")
    assert "calendar" in response.context and response.context["mode"] == "calendar"

    response = django_app.get(reverse("core:event_list"), user=volunteer)
    assert "calendar" in response.context and response.context["mode"] == "calendar"
    response = response.click("fa-calendar-day")
    assert "calendar" not in response.context and response.context["mode"] == "day"


def test_list_and_calendar_dont_display_event_without_view_permission(django_app, volunteer, event):
    # sanity check the event is there
    response = django_app.get(reverse("core:event_list"), user=volunteer)
    assert event.title in response

    # remove view permissions by removing group membership
    volunteer.groups.set([])
    volunteer.save()

    # event should not show up in list and calendar
    response = django_app.get(reverse("core:event_list"), user=volunteer)
    assert event.title not in response
    response = django_app.get(
        f"{reverse('core:event_list')}?mode=calendar&date={event.shifts.first().start_time:%Y-%m-%d}",
        user=volunteer,
    )
    assert event.title not in response


def test_event_filter_participation_state(django_app, volunteer, event, conflicting_event):
    # event_list also exists in calendar_view
    response = django_app.get(
        f"{reverse('core:event_list')}?mode=calendar&date={event.get_start_time():%Y-%m-%d}",
        user=volunteer,
    )

    assert set(response.context["event_list"]) == {event, conflicting_event}
    assert event.title in response and conflicting_event.title in response

    filter_form = response.forms["filter-form"]
    filter_form["state"] = "confirmed"
    response = filter_form.submit()
    assert set(response.context["event_list"]) == {conflicting_event}
    assert event.title not in response and conflicting_event.title in response

    filter_form["state"] = "requested-confirmed"
    response = filter_form.submit()
    assert set(response.context["event_list"]) == {conflicting_event}
    assert event.title not in response and conflicting_event.title in response

    filter_form["state"] = "no-response"
    response = filter_form.submit()
    assert set(response.context["event_list"]) == {event}
    assert event.title in response and conflicting_event.title not in response


def test_event_filter_query_string(django_app, volunteer, event, conflicting_event):
    response = django_app.get(
        f"{reverse('core:event_list')}?mode=calendar&date={event.get_start_time():%Y-%m-%d}",
        user=volunteer,
    )
    filter_form = response.forms["filter-form"]
    filter_form["query"] = event.title
    response = filter_form.submit()
    assert set(response.context["event_list"]) == {event}
    assert event.title in response and conflicting_event.title not in response


def test_event_filter_event_type(
    django_app, volunteer, event, conflicting_event, training_event_type
):
    response = django_app.get(
        f"{reverse('core:event_list')}?mode=calendar&date={event.get_start_time():%Y-%m-%d}",
        user=volunteer,
    )
    filter_form = response.forms["filter-form"]
    filter_form["types"] = [training_event_type.id]
    response = filter_form.submit()
    assert set(response.context["event_list"]) == {conflicting_event}
    assert event.title not in response and conflicting_event.title in response


def test_event_filter_pending_disposition(django_app, planner, volunteer, event):
    # first look for pending dispo events and find none
    filter_form = django_app.get(
        f"{reverse('core:event_list')}?mode=calendar&date={event.get_start_time():%Y-%m-%d}",
        user=planner,
    ).forms["filter-form"]
    filter_form["state"] = "pending"
    response = filter_form.submit()
    assert set(response.context["event_list"]) == set()
    assert event.title not in response

    # request by the volunteer
    django_app.get(event.get_absolute_url(), user=volunteer).form.submit(
        name="signup_choice", value="sign_up"
    )

    # now find the pending event
    filter_form = django_app.get(
        f"{reverse('core:event_list')}?date={event.get_start_time():%Y-%m-%d}",
        user=planner,
    ).forms["filter-form"]
    filter_form["state"] = "pending"
    response = filter_form.submit()
    assert set(response.context["event_list"]) == {event}
    assert event.title in response


def test_event_filter_time(django_app, planner, event):
    filter_form = django_app.get(reverse("core:event_list"), user=planner).forms["filter-form"]
    filter_form["date"] = f"{event.get_start_time() + timedelta(days=14):%Y-%m-%d}"
    assert set(filter_form.submit().context["event_list"]) == set()
    filter_form["direction"] = "until"
    assert set(filter_form.submit().context["event_list"]) == {event}


def test_signup_from_day_calendar(django_app, volunteer, event):
    response = django_app.get(
        f"{reverse('core:event_list')}?mode=day&date={event.get_start_time():%Y-%m-%d}",
        user=volunteer,
    )
    response.forms[1].submit(name="signup_choice", value="sign_up").follow()
    assert LocalParticipation.objects.filter(shift__event=event, user=volunteer).exists()


def test_day_mode_filter(django_app, volunteer, event, conflicting_event):
    response = django_app.get(
        f"{reverse('core:event_list')}?mode=day&date={event.get_start_time():%Y-%m-%d}",
        user=volunteer,
    )
    filter_form = response.forms["filter-form"]
    filter_form["query"] = event.title
    response = filter_form.submit()
    assert set(response.context["event_list"]) == {event}
    assert event.title in response and conflicting_event.title not in response
