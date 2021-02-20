import pytest


@pytest.mark.django_db
def test_accounts_login(django_app):
    resp = django_app.get("/accounts/login/")
    assert resp.status_code == 200, "Should return a 200 status code"
