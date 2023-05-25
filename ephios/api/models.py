from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
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

    def get_absolute_url(self):
        return reverse("api:settings-oauth-app-detail", args=[str(self.id)])


class AccessToken(AbstractAccessToken):
    class Meta(AbstractAccessToken.Meta):
        swappable = "OAUTH2_PROVIDER_ACCESS_TOKEN_MODEL"

    description = models.TextField(
        verbose_name=_("Description"),
        blank=True,
    )

    revoked = models.DateTimeField(null=True)

    # make expires nullable for non-expiring user tokens
    expires = models.DateTimeField(
        null=True,
    )

    def is_expired(self):
        if not self.expires:
            return False  # never expires
        return timezone.now() >= self.expires

    def is_valid(self, scopes=None):
        # expand super to include revoked check
        return self.revoked is None and super().is_valid(scopes)

    def __str__(self):
        if self.application:
            return _("Access Token") + f" #{self.id}"
        return _("User Token") + f" #{self.id}"

    def revoke_related(self):
        """
        Revoke this token and other types of related OAuth2 tokens.
        """
        try:
            # aquired from OAuth2 refresh token, so revoke that one (which will revoke this access token as well)
            self.refresh_token.revoke()
        except RefreshToken.DoesNotExist:
            # manually created token (?), so revoke it directly
            self.revoke()

    def revoke(self):
        if self.revoked is None:
            self.revoked = timezone.now()
            self.save(update_fields=["revoked"])


class RefreshToken(AbstractRefreshToken):
    class Meta(AbstractRefreshToken.Meta):
        swappable = "OAUTH2_PROVIDER_REFRESH_TOKEN_MODEL"


class IDToken(AbstractIDToken):
    class Meta(AbstractIDToken.Meta):
        swappable = "OAUTH2_PROVIDER_ID_TOKEN_MODEL"


class Grant(AbstractGrant):
    class Meta(AbstractGrant.Meta):
        swappable = "OAUTH2_PROVIDER_GRANT_MODEL"
