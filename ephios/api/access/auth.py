from oauth2_provider.contrib.rest_framework import OAuth2Authentication


class CustomOAuth2Authentication(OAuth2Authentication):
    """
    Overwrites the default OAuth2Authentication to not allow inactive users to authenticate.
    """

    def authenticate(self, request):
        oauth_result = super().authenticate(request)
        if oauth_result is None:
            return None
        user, token = oauth_result
        if not user.is_active:
            return None
        return user, token
