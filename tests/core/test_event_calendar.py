from django.urls import reverse


def test_calendar_display(client, volunteer, event):
    # we are using the django test client here because we couldn't get the session stuff to
    # work with pytest. Don't copy this!
    session = client.session
    session["event_list_view_type"] = "calendar"
    session.save()
    client.force_login(volunteer)
    response = client.get(reverse("core:event_list"))
    assert response.status_code == 200
    assert "core/event_calendar.html" in response.template_name


def test_calendar_display_restricitions(client, volunteer, event):
    # we are using the django test client here because we couldn't get the session stuff to
    # work with pytest. Don't copy this!
    volunteer.groups.set([])
    volunteer.save()
    session = client.session
    session["event_list_view_type"] = "calendar"
    session.save()
    client.force_login(volunteer)
    shift = event.shifts.first()
    response = client.get(
        f"{reverse('core:event_list')}?year={shift.start_time.year}&month={shift.start_time.month}"
    )
    assert response.status_code == 200
    assert "core/event_calendar.html" in response.template_name
    assert event.title not in response.rendered_content
