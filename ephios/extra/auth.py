from typing import Any, Dict
from urllib.parse import urljoin

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import SuspiciousOperation
from django.urls import reverse
from jwt import InvalidTokenError
from oauthlib.oauth2 import WebApplicationClient
from requests_oauthlib import OAuth2Session
from urllib3.exceptions import RequestError

from ephios.core.models.users import IdentityProvider


class EphiosOIDCAB(ModelBackend):
    def decode_jwt_token(self, token: str) -> Dict[str, Any]:
        jwks_client = jwt.PyJWKClient(self.provider.jwks_uri)
        header = jwt.get_unverified_header(token)
        key = jwks_client.get_signing_key(header["kid"]).key
        decoded = jwt.decode(token, key, [header["alg"]], audience=self.provider.client_id)
        return decoded

    def create_user(self, claims):
        user = get_user_model()(email=claims.get("email"))
        user.set_unusable_password()
        user.first_name = claims.get("given_name", "")
        user.last_name = claims.get("family_name", "")
        user.save()
        if hasattr(self, "provider") and self.provider.default_groups.exists():
            user.groups.add(*self.provider.default_groups.all())

        return user

    def update_user(self, user, claims):
        if "given_name" in claims:
            user.first_name = claims["given_name"]
        if "family_name" in claims:
            user.last_name = claims["family_name"]
        user.save()
        if hasattr(self, "provider") and self.provider.default_groups.exists():
            user.groups.add(*self.provider.default_groups.all())
        return user

    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            self.provider = IdentityProvider.objects.get(id=request.session["oidc_provider"])
            oauth = OAuth2Session(
                client=WebApplicationClient(client_id=self.provider.client_id),
                redirect_uri=urljoin(settings.GET_SITE_URL(), reverse("core:oidc_callback")),
            )
            token = oauth.fetch_token(
                self.provider.token_endpoint,
                code=request.GET["code"],
                client_secret=self.provider.client_secret,
                include_client_id=True,
            )
            self.decode_jwt_token(
                token["id_token"]
            )  # this already contains the claims for the tested OP, check the standard to see if we can omit the call to the user endpoint
            user_info = oauth.request("GET", self.provider.userinfo_endpoint).json()
            if "email" not in user_info:
                raise SuspiciousOperation("OIDC client did not return email address")
            users = get_user_model().objects.filter(email__iexact=user_info["email"])
            if len(users) == 1:
                return self.update_user(users.first(), user_info)
            if len(users) > 1:
                raise SuspiciousOperation("Multiple users with same email address")
            return self.create_user(user_info)
        except (
            KeyError,
            ValueError,
            ConnectionError,
            RequestError,
            IdentityProvider.DoesNotExist,
            InvalidTokenError,
        ):
            return None
