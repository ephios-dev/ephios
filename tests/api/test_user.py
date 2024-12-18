from django.urls import reverse


def test_user_profile_list(django_app, groups, superuser):
    response = django_app.get(reverse("api:userprofile-list"), user=superuser)
    assert superuser.email in response


def test_api_user_profile_by_email(django_app, superuser):
    superuser.email = "special-char.123@toplevel.berlin"
    superuser.save()
    response = django_app.get(
        reverse(
            "api:user-by-email-detail",
            kwargs={
                "email": superuser.email,
            },
        ),
        user=superuser,
    )
    assert superuser.email in response


def test_manager_can_view_users(django_app, groups, manager):
    response = django_app.get(reverse("api:userprofile-list"), user=manager)
    assert manager.email in response


def test_volunter_cannot_view_users(django_app, groups, volunteer):
    response = django_app.get(reverse("api:userprofile-list"), user=volunteer, expect_errors=True)
    assert response.status_code == 403
