import secrets
from datetime import date

import pytest
from django.urls import reverse
from oauth2_provider.generators import generate_client_secret

from ephios.api.models import AccessToken, Application
from ephios.plugins.federation.models import (
    FederatedEventShare,
    FederatedGuest,
    FederatedHost,
    FederatedUser,
    InviteCode,
)


@pytest.fixture
def invite_code():
    return InviteCode.objects.create(url="http://localhost:8000")


@pytest.fixture
def federation():
    access_token = AccessToken.objects.create(token=secrets.token_hex())
    oauth_client_secret = generate_client_secret()
    oauth_app = Application.objects.create(
        client_secret=oauth_client_secret,
        client_type=Application.CLIENT_CONFIDENTIAL,
        authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
        redirect_uris=f"http://localhost:8080/{reverse('federation:oauth_callback')}",
    )
    host = FederatedHost.objects.create(
        name="Test",
        url="http://localhost:8000",
        access_token=access_token.token,
        oauth_application=oauth_app,
    )
    guest = FederatedGuest.objects.create(
        name="Test",
        url="http://localhost:8080",
        access_token=access_token,
        client_id=oauth_app.client_id,
        client_secret=oauth_client_secret,
    )
    return host, guest


@pytest.fixture
def federated_user(federation):
    host, guest = federation
    return FederatedUser.objects.create(
        email="test@localhost",
        display_name="Federated Testuser",
        date_of_birth=date(2000, 1, 1),
        phone="12345",
        federated_instance=guest,
    )


@pytest.fixture
def federated_event(event, federation):
    host, guest = federation
    share = FederatedEventShare.objects.create(event=event)
    share.shared_with.add(guest)
    return event
