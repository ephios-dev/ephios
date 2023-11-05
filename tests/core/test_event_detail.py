from django.urls import reverse


def test_slug_redirect(django_app, volunteer, event):
    response = django_app.get(
        reverse("core:event_detail", kwargs=dict(pk=event.pk, slug="nottheactualslug")),
        user=volunteer,
    )
    assert response.location  # is a redirect
    response = response.follow()
    assert event.title in response


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
