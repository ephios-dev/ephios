from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.plumbing import build_bearer_security_scheme_object
from oauth2_provider.contrib.rest_framework import OAuth2Authentication

from ephios.api.models import AccessToken
from ephios.core.models import UserProfile


class TokenScheme(OpenApiAuthenticationExtension):
    target_class = "ephios.api.access.auth.CustomOAuth2Authentication"
    name = "tokenAuth"
    match_subclasses = True
    priority = 1

    def get_security_definition(self, auto_schema):
        return build_bearer_security_scheme_object(
            header_name="Authorization",
            token_prefix="Bearer",
        )


class CustomOAuth2Authentication(OAuth2Authentication):
    """
    Overwrites the default OAuth2Authentication to not allow inactive users to authenticate.
    """

    def authenticate(self, request):
        oauth_result = super().authenticate(request)
        if oauth_result is None:
            return None
        user, token = oauth_result
        if user is not None and not user.is_active:
            return None
        return user, token


def revoke_all_access_tokens(user: UserProfile):
    for access_token in AccessToken.objects.filter(user=user):
        access_token.revoke_related()
