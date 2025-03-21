from django.urls import reverse


def test_slug_redirect(django_app, volunteer, event):
    response = django_app.get(
        reverse("core:event_detail", kwargs=dict(pk=event.pk, slug="nottheactualslug")),
        user=volunteer,
    )
    assert response.location  # is a redirect
    response = response.follow()
    assert event.title in response


def test_anon_redirect(django_app, event):
    django_app.get(
        reverse("core:event_detail", kwargs=dict(pk=event.pk, slug="nottheactualslug")),
    ).follow()


def test_event_slug_with_empty_name(django_app, volunteer, event):
    event.title = ""
    event.save()
    response = django_app.get(
        reverse("core:event_detail", kwargs=dict(pk=event.pk, slug="nottheactualslug")),
        user=volunteer,
    )
    assert response.location  # is a redirect
    response = response.follow()
    assert event.description in response


def test_show_disposition_button(django_app, volunteer, planner, event):
    assert (
        "Disposition"
        not in django_app.get(
            reverse("core:event_detail", kwargs=dict(pk=event.pk, slug="nottheactualslug")),
            user=volunteer,
        ).follow()
    )
    assert (
        "Disposition"
        in django_app.get(
            reverse("core:event_detail", kwargs=dict(pk=event.pk, slug="nottheactualslug")),
            user=planner,
        ).follow()
    )


def test_edit_permissions(django_app, volunteer, manager, groups, event):
    shift_id = event.shifts.first().pk
    response = django_app.get(
        reverse("core:event_detail", kwargs=dict(pk=event.pk, slug="nottheactualslug")),
        user=volunteer,
    ).follow()
    assert "Add another shift" not in response
    assert "Edit" not in response.html.find(id=f"shift-{shift_id}").text

    response = django_app.get(
        reverse("core:event_detail", kwargs=dict(pk=event.pk, slug="nottheactualslug")),
        user=manager,
    ).follow()
    assert "Add another shift" in response
    assert "Edit" in response.html.find(id=f"shift-{shift_id}").text
