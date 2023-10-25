from datetime import date
from functools import reduce
from typing import Any, Dict
from urllib.parse import urljoin

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Group
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
        return self.update_user(user, claims)

    def update_user(self, user, claims):
        if "name" in claims:
            user.display_name = claims["name"]
        elif "given_name" in claims and "family_name" in claims:
            user.display_name = f"{claims['given_name']} {claims['family_name']}"
        if "phone_number" in claims:
            user.phone = claims["phone_number"]
        if "birthdate" in claims:
            try:
                user.date_of_birth = date.fromisoformat(claims["birthdate"])
            except ValueError:
                pass
        user.save()
        if self.provider.group_claim:
            groups = set(self.provider.default_groups.all())
            groups_in_claims = (
                reduce(
                    lambda d, key: d.get(key, None) if isinstance(d, dict) else None,
                    self.provider.group_claim.split("."),
                    claims,
                )
                or []
            )
            for group_name in groups_in_claims:
                try:
                    groups.add(Group.objects.get(name__iexact=group_name))
                except Group.DoesNotExist:
                    if self.provider.create_missing_groups:
                        groups.add(Group.objects.create(name=group_name))
            user.groups.set(groups)
        elif self.provider.default_groups.exists():
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
