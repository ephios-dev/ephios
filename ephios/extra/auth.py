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
        user.first_name = claims.get("given_name", "")
        user.last_name = claims.get("family_name", "")
        user.save()

        return user
