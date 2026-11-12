from django.urls import reverse

from ephios.plugins.eventlistquickfilters.models import EventListQuickFilter


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
    assert response.html.find("a", href=reverse("eventlistquickfilters:eventlistquickfilter_list"))
    assert "Create new Event List Quick Filter" in response.text
    assert response.form["position"].value == "1"
    response.form["label"] = "Only Services"
    response.form["filter_types"] = [service_event_type.id]
    response.form["visible_for_groups"] = [volunteers.id]
    response.form["default_for_groups"] = [volunteers.id]
    response = response.form.submit()
    response = response.follow()
    assert volunteers.name in response.text
    assert response.html.find("span", class_="badge-eventtype", string=str(service_event_type))
    assert response.html.find("span", string=volunteers.name) is None
    assert "Event list quick filter saved successfully." in response.text

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


def test_empty_type_selection_must_be_default_for_visible_groups(django_app, superuser, groups):
    _, _, volunteers = groups
    response = django_app.get(
        reverse("eventlistquickfilters:eventlistquickfilter_list"), user=superuser
    )
    response = response.click(".*dd.*ilter.*")
    response.form["label"] = "All event types"
    response.form["filter_types"] = []
    response.form["visible_for_groups"] = [volunteers.id]
    response.form["default_for_groups"] = []
    response = response.form.submit()

    assert "filter_types" in response.context["form"].errors
    assert "select every event type instead" in response.text

    response.form["default_for_groups"] = [volunteers.id]
    response = response.form.submit()
    assert response.status_code == 302
    response = response.follow()
    assert "Event list quick filter saved successfully." in response.text

    quick_filter = EventListQuickFilter.objects.get(label="All event types")
    response = django_app.get(
        reverse("eventlistquickfilters:eventlistquickfilter_delete", args=[quick_filter.pk]),
        user=superuser,
    )
    assert "Delete Event List Quick Filter" in response.text
    assert "All event types" in response.text
    assert response.html.find("a", href=reverse("eventlistquickfilters:eventlistquickfilter_list"))
    response = response.form.submit().follow()
    assert "Event list quick filter deleted successfully." in response.text


def test_new_filter_position_defaults_to_one_more_than_existing_max(django_app, superuser):
    EventListQuickFilter.objects.create(label="Existing", position=8)
    response = django_app.get(
        reverse("eventlistquickfilters:eventlistquickfilter_add"), user=superuser
    )

    assert response.form["position"].value == "9"
