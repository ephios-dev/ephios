from django.urls import reverse
from guardian.shortcuts import remove_perm


def test_api_event_list_rejects_anonymous_get(django_app, event):
    response = django_app.get(reverse("api:event-list"), status=403)
    assert event.title not in response
    assert "Authentication credentials were not provided." in response


def test_browseable_api_renders(django_app, event, planner):
    response = django_app.get(
        reverse("api:event-list"),
        user=planner,
        status=200,
        headers={"Accept": "text/html"},
    )
    # logged in user only shown in browseable api
    assert str(planner) in response.text


def test_api_event_list_view_permission_checks(django_app, event, planner, groups, volunteer):
    django_app.get(
        reverse("api:event-detail", kwargs=dict(pk=event.pk)), user=volunteer, status=200
    )
    assert event.title in django_app.get(reverse("api:event-list"), user=planner, status=200)
    assert event.title in django_app.get(reverse("api:event-list"), user=volunteer, status=200)

    # make event invisible to volunteers
    _, _, volunteers = groups
    remove_perm("view_event", volunteers, event)

    django_app.get(
        reverse("api:event-detail", kwargs=dict(pk=event.pk)), user=volunteer, status=404
    )
    django_app.get(reverse("api:event-detail", kwargs=dict(pk=event.pk)), user=planner, status=200)
    assert event.title in django_app.get(reverse("api:event-list"), user=planner, status=200)
    assert event.title not in django_app.get(
        reverse("api:event-list"), user=volunteer, status=200
    ), "Event is visible even though user does not have view permissions."


def test_api_event_list_cant_be_posted(csrf_exempt_django_app, manager):
    assert (
        b"You do not have permission to perform this action."
        in csrf_exempt_django_app.post(
            reverse("api:event-list"), {"title": "New event"}, status=403, user=manager
        ).body
    )
