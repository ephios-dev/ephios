from oauth2_provider.models import (
    AbstractAccessToken,
    AbstractApplication,
    AbstractGrant,
    AbstractIDToken,
    AbstractRefreshToken,
    ApplicationManager,
)


class Application(AbstractApplication):
    objects = ApplicationManager()

    class Meta(AbstractApplication.Meta):
        swappable = "OAUTH2_PROVIDER_APPLICATION_MODEL"

    def natural_key(self):
        return (self.client_id,)


class AccessToken(AbstractAccessToken):
    class Meta(AbstractAccessToken.Meta):
        swappable = "OAUTH2_PROVIDER_ACCESS_TOKEN_MODEL"


class RefreshToken(AbstractRefreshToken):
    class Meta(AbstractRefreshToken.Meta):
        swappable = "OAUTH2_PROVIDER_REFRESH_TOKEN_MODEL"


class IDToken(AbstractIDToken):
    class Meta(AbstractIDToken.Meta):
        swappable = "OAUTH2_PROVIDER_ID_TOKEN_MODEL"


class Grant(AbstractGrant):
    class Meta(AbstractGrant.Meta):
        swappable = "OAUTH2_PROVIDER_GRANT_MODEL"
