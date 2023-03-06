import oauth2_provider.models


class AccessToken(oauth2_provider.models.AbstractAccessToken):
    class Meta(oauth2_provider.models.AbstractAccessToken.Meta):
        swappable = "OAUTH2_PROVIDER_ACCESS_TOKEN_MODEL"
