import secrets

import pytest

from ephios.api.models import AccessToken, Application
from ephios.plugins.federation.models import FederatedGuest, FederatedHost, InviteCode


@pytest.fixture
def invite_code():
    return InviteCode.objects.create(url="http://localhost:8000")


@pytest.fixture
def federation():
    def _setup(url):
        access_token = AccessToken.objects.create(token=secrets.token_hex())
        oauth_app = Application.objects.create()
        host = FederatedHost.objects.create(
            name="Test",
            url=url,
            access_token=access_token.token,
            oauth_application=oauth_app,
        )
        guest = FederatedGuest.objects.create(
            name="Test",
            url=url,
            access_token=access_token,
            client_id=oauth_app.client_id,
            client_secret=oauth_app.client_secret,
        )
        return host, guest

    return _setup
