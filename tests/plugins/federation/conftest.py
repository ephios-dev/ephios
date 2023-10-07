import secrets

import pytest
from django.urls import reverse
from oauth2_provider.generators import generate_client_secret

from ephios.api.models import AccessToken, Application
from ephios.plugins.federation.models import FederatedGuest, FederatedHost, InviteCode


@pytest.fixture
def invite_code():
    return InviteCode.objects.create(url="http://localhost:8000")


@pytest.fixture
def federation():
    def _setup(url):
        access_token = AccessToken.objects.create(token=secrets.token_hex())
        oauth_client_secret = generate_client_secret()
        oauth_app = Application.objects.create(
            client_secret=oauth_client_secret,
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
            redirect_uris=f"{url}{reverse('federation:oauth_callback')}",
        )
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
            client_secret=oauth_client_secret,
        )
        return host, guest

    return _setup
