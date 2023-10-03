from django.contrib.auth import get_user_model
from django.core.exceptions import SuspiciousOperation
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

from ephios.core.models.users import EphiosOIDCClient


class EphiosOIDCAB(OIDCAuthenticationBackend):
    def __init__(self, *args, **kwargs):
        self.client = None
        self.UserModel = get_user_model()

    def create_user(self, claims):
        user = get_user_model()(email=claims.get("email"))
        user.set_unusable_password()
        user.first_name = claims.get("given_name", "")
        user.last_name = claims.get("family_name", "")
        user.save()

        return user

    def update_user(self, user, claims):
        if "given_name" in claims:
            user.first_name = claims["given_name"]
        if "family_name" in claims:
            user.last_name = claims["family_name"]
        user.save()
        return user

    def authenticate(self, request, **kwargs):
        try:
            self.client = EphiosOIDCClient.objects.get(id=request.session["oidc_client_id"])
            super().__init__(request)
            request.session.pop("oidc_client_id")
            return super().authenticate(request, **kwargs)
        except (KeyError, EphiosOIDCClient.DoesNotExist):
            raise SuspiciousOperation("Could not determine OIDC client")

    def get_settings(self, attr, *args):
        return self.client and self.client.get_mozilla_oidc_attribute(attr, *args)
