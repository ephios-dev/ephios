from django.urls import reverse


def test_slug_redirect(django_app, volunteer, event):
    response = django_app.get(
        reverse("core:event_detail", kwargs=dict(pk=event.pk, slug="nottheactualslug")),
        user=volunteer,
    )
    assert response.location  # is a redirect
    response = response.follow()
    assert event.title in response


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
