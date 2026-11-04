from django.urls import reverse


def test_eventlistquickfilter_usage_flow(
    django_app,
    superuser,
    volunteer,
    groups,
    event,
    conflicting_event,
    service_event_type,
    training_event_type,
):
    managers, planners, volunteers = groups
    response = django_app.get(
        reverse("eventlistquickfilters:eventlistquickfilter_list"), user=superuser
    )
    response = response.click(".*dd.*ilter.*")  # pattern for "add Event List Quick Filter"
    response.form["label"] = "Only Services"
    response.form["filter_types"] = [service_event_type.id]
    response.form["visible_for_groups"] = [volunteers.id]
    response.form["default_for_groups"] = [volunteers.id]
    response.form.submit()

    response = django_app.get(reverse("core:event_list"), user=superuser)
    assert "Only Services" not in response.text, "superuser should not see the new filter button"
    assert len(response.context["event_list"]) == 2, (
        "superuser should see all events without any filtering"
    )

    response = django_app.get(reverse("core:event_list"), user=volunteer)
    assert "Only Services" in response.text, "volunteer should see the new filter button"
    assert conflicting_event not in response.context["event_list"], (
        "conflicting event should be filtered out by the default filter"
    )
