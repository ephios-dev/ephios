from django.db import models
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


class AccessToken(AbstractAccessToken):
    class Meta(AbstractAccessToken.Meta):
        swappable = "OAUTH2_PROVIDER_ACCESS_TOKEN_MODEL"

    description = models.TextField(
        verbose_name=_("Description"),
        blank=True,
    )

    # make expires nullable for non-expiring user tokens
    expires = models.DateTimeField(
        null=True,
    )

    def is_expired(self):
        if not self.expires:
            return False  # never expires
        return timezone.now() >= self.expires

    @property
    def name(self):
        if self.application and self.application.name:
            return f"{self.application.name} #{self.id}"
        return _("User-Token") + f" #{self.id}"

    def __str__(self):
        return self.name

    def revoke(self):  # todo actually use this in the view, currently a plain delete view
        self.expires = timezone.now()
        self.save(update_fields=["expires"])


class RefreshToken(AbstractRefreshToken):
    class Meta(AbstractRefreshToken.Meta):
        swappable = "OAUTH2_PROVIDER_REFRESH_TOKEN_MODEL"


class IDToken(AbstractIDToken):
    class Meta(AbstractIDToken.Meta):
        swappable = "OAUTH2_PROVIDER_ID_TOKEN_MODEL"


class Grant(AbstractGrant):
    class Meta(AbstractGrant.Meta):
        swappable = "OAUTH2_PROVIDER_GRANT_MODEL"
