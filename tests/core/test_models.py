from datetime import datetime

from django.urls import reverse
from django.utils import timezone


def test_user_qualifications(qualified_volunteer, qualifications, tz):
    assert timezone.now().year < 2064  # update tests
    assert set(qualified_volunteer.qualifications) == {
        qualifications.nfs,
        qualifications.c,
        qualifications.b,
    }
    assert qualified_volunteer.qualifications.get(id=qualifications.c.id).expires == datetime(
        2090, 4, 1
    ).astimezone(tz)
    assert qualified_volunteer.qualifications.get(id=qualifications.b.id).expires is None
    assert qualified_volunteer.qualifications.get(id=qualifications.nfs.id).expires == datetime(
        2064, 4, 1
    ).astimezone(tz)


def test_case_insensitive_login(django_app, volunteer, django_username_field):
    volunteer.set_password("test")
    volunteer.save()
    form = django_app.get(reverse("login")).form
    form["username"] = volunteer.email.upper()
    form["password"] = "test"
    response = form.submit()
    assert response.location == reverse("core:home")


def test_case_insensitive_email_constraint(django_app, volunteer, manager, groups):
    form = django_app.get(reverse("core:userprofile_create"), user=manager).form
    form["email"] = volunteer.email.upper()
    form["display_name"] = "Test User"
    form["date_of_birth"] = "2000-01-01"
    response = form.submit()
    assert response.status_code == 200
    assert "email" in response.context["form"].errors
