import pytest
from django.urls import reverse

from ephios.api.models import AccessToken


def test_creating_a_user_token(django_app, volunteer):
    response = django_app.get(
        reverse("api:settings-access-token-create"),
        user=volunteer,
    )
    response.form["description"] = "door sign raspebrry pi"
    response.form["scope"] = ["PUBLIC_READ", "PUBLIC_WRITE"]
    response = response.form.submit().follow()
    # reveal token
    access_token = AccessToken.objects.get()
    assert access_token.token in response
    assert access_token.scope == "PUBLIC_READ PUBLIC_WRITE"
    response = response.click("Done")
    assert "door sign raspebrry pi" in response


@pytest.fixture
def user_token(volunteer):
    return AccessToken.objects.create(
        user=volunteer,
        description="door sign raspebrry pi",
        scope="PUBLIC_READ PUBLIC_WRITE",
        token="ABCtesttokenDEF123",
    )


def test_events_endpoint_with_user_token(django_app, event, user_token):
    response = django_app.get(
        reverse("api:event-list"), headers={"Authorization": f"Bearer {user_token.token}"}
    )
    assert event.title in response

    # Token out of scope
    user_token.scope = "PUBLIC_WRITE"
    user_token.save()
    django_app.get(
        reverse("api:event-list"),
        headers={"Authorization": f"Bearer {user_token.token}"},
        status=403,
    )


def test_user_can_revoke_own_user_token(django_app, user_token):
    response = django_app.get(reverse("api:settings-access-token-list"), user=user_token.user)
    # form is the revoke button
    response = response.form.submit().follow()
    assert "Token was revoked" in response
    assert not AccessToken.objects.get().is_valid()


def test_manager_can_revoke_password_and_user_token(django_app, user_token, groups, manager):
    response = django_app.get(
        reverse("core:userprofile_password_token_revoke", kwargs=dict(pk=user_token.user.pk)),
        user=manager,
    )
    response.form.submit().follow()
    assert not AccessToken.objects.get().is_valid()


def test_inactive_accounts_tokens_dont_work(django_app, user_token):
    user_token.user.is_active = False
    user_token.user.save()
    django_app.get(
        reverse("api:event-list"),
        headers={"Authorization": f"Bearer {user_token.token}"},
        status=403,
    )


def test_manager_cannot_reveal_volunteers_token(django_app, user_token, manager):
    django_app.get(
        reverse("api:settings-access-token-reveal", kwargs=dict(pk=user_token.pk)),
        user=user_token.user,
    )
    django_app.get(
        reverse("api:settings-access-token-reveal", kwargs=dict(pk=user_token.pk)),
        user=manager,
        status=403,
    )
