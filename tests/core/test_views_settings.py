from django.urls import reverse


def test_enabling_and_disabling(django_app, superuser):
    response = django_app.get(reverse("core:settings_instance"), user=superuser)
    assert response


def test_settings_calendar(django_app, volunteer):
    response = django_app.get(reverse("core:settings_calendar"), user=volunteer)
    calendar_url = response.html.find("input", id="calendar-url")["value"]
    assert calendar_url

    response = django_app.get(calendar_url, user=volunteer)
    assert response


def test_settings_instance(django_app, superuser):
    response = django_app.get(reverse("core:settings_instance"), user=superuser)
    assert "System health" in response.html.text
