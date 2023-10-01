from django.contrib.auth import get_user_model
from mozilla_django_oidc.auth import OIDCAuthenticationBackend


class EphiosOIDCAB(OIDCAuthenticationBackend):
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

    @staticmethod
    def get_settings(attr, *args):
        test = {
            "OIDC_RP_CLIENT_ID": "3c23327f-416a-4862-b8a8-928d1b7bcfc9",
            "OIDC_RP_CLIENT_SECRET": "827f4954956a0a74fa4af0205339cb3d4e83f02ecdb199d9223519b076edb0a5951dc3b41d791a97381747ea84327aa9aa598f913b187d21656d0823351394ee",
            "OIDC_RP_SCOPES": "openid profile email",
            "OIDC_RP_SIGN_ALGO": "RS256",
            "OIDC_OP_AUTHORIZATION_ENDPOINT": "https://oidc.hpi.de/auth",
            "OIDC_AUTHENTICATION_CALLBACK_URL": "oidc_authentication_callback",
            "OIDC_OP_TOKEN_ENDPOINT": "https://oidc.hpi.de/token",
            "OIDC_OP_JWKS_ENDPOINT": "https://oidc.hpi.de/certs",
            "OIDC_OP_USER_ENDPOINT": "https://oidc.hpi.de/me",
        }
        return test.get(attr, args[0] if args else None)
