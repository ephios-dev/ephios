import base64
import dataclasses
import datetime
import json
from secrets import token_hex

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from ephios.api.models import AccessToken, Application
from ephios.core.models import AbstractParticipation, Event, Qualification
from ephios.core.models.events import PARTICIPATION_LOG_CONFIG
from ephios.core.signup.participants import AbstractParticipant
from ephios.modellogging.log import ModelFieldsLogConfig, register_model_for_logging


class FederatedGuest(models.Model):
    name = models.CharField(max_length=255)
    url = models.URLField(verbose_name=_("URL"))

    # this ephios instance is sending events to the guest
    # therefore this instance is registered as an oauth application
    # on the guest instance to access user data like qualifications
    access_token = models.OneToOneField(AccessToken, on_delete=models.CASCADE)
    client_id = models.CharField(max_length=255)
    client_secret = models.CharField(max_length=255)

    def __str__(self):
        return str(self.name)

    class Meta:
        verbose_name = _("federated guest")
        verbose_name_plural = _("federated guests")


register_model_for_logging(
    FederatedGuest,
    ModelFieldsLogConfig(
        unlogged_fields=[
            "id",
            "access_token",
            "client_secret",
        ],
    ),
)


class FederatedHost(models.Model):
    name = models.CharField(max_length=255)
    url = models.URLField(verbose_name=_("URL"))
    access_token = models.CharField(max_length=255)

    # this ephios instance is receiving events from the host
    # therefore the host is registered as an oauth application
    # on this instance to acceess user data like qualifications
    oauth_application = models.OneToOneField(Application, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.name)

    class Meta:
        verbose_name = _("federated host")
        verbose_name_plural = _("federated hosts")


register_model_for_logging(
    FederatedHost,
    ModelFieldsLogConfig(
        unlogged_fields=[
            "id",
            "access_token",
        ],
    ),
)


class InviteCode(models.Model):
    code = models.CharField(max_length=255, default=token_hex)
    url = models.URLField(verbose_name=_("URL"))
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return _("Federation invite code for {url}").format(url=self.url)

    @property
    def is_expired(self):
        return timezone.now() - self.created_at > datetime.timedelta(hours=48)

    def get_share_string(self):
        return base64.b64encode(
            json.dumps(
                {"guest_url": self.url, "code": self.code, "host_url": settings.GET_SITE_URL()}
            ).encode()
        ).decode()

    class Meta:
        verbose_name = _("invite code")
        verbose_name_plural = _("invite codes")


register_model_for_logging(
    InviteCode,
    ModelFieldsLogConfig(
        unlogged_fields=[
            "id",
            "code",
            "created_at",
        ],
    ),
)


class FederatedEventShare(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    shared_with = models.ManyToManyField(FederatedGuest)

    def __str__(self):
        return _("Federated event share for {event}").format(event=self.event)

    class Meta:
        verbose_name = _("federated event share")
        verbose_name_plural = _("federated event shares")


register_model_for_logging(
    FederatedEventShare,
    ModelFieldsLogConfig(),
)


class FederatedUser(models.Model):
    email = models.EmailField(_("email address"))
    display_name = models.CharField(_("name"), max_length=254)
    date_of_birth = models.DateField(_("date of birth"))
    phone = models.CharField(_("phone number"), max_length=254, blank=True)
    qualifications = models.ManyToManyField(Qualification)
    federated_instance = models.ForeignKey(FederatedGuest, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return _("Federated user {display_name}").format(display_name=self.display_name)

    def as_participant(self) -> "FederatedParticipant":
        return FederatedParticipant(
            display_name=self.display_name,
            qualifications=self.qualifications.all(),
            date_of_birth=self.date_of_birth,
            email=self.email,
            federated_user=self,
        )

    class Meta:
        verbose_name = _("federated user")
        verbose_name_plural = _("federated users")


register_model_for_logging(
    FederatedUser,
    ModelFieldsLogConfig(),
)


@dataclasses.dataclass(frozen=True)
class FederatedParticipant(AbstractParticipant):
    federated_user: FederatedUser

    def new_participation(self, shift):
        return FederatedParticipation(shift=shift, federated_user=self.federated_user)

    def participation_for(self, shift):
        try:
            return FederatedParticipation.objects.get(
                shift=shift, federated_user=self.federated_user
            )
        except FederatedParticipation.DoesNotExist:
            return None

    def all_participations(self):
        return FederatedParticipation.objects.filter(federated_user=self.federated_user)

    def reverse_signup_action(self, shift):
        return reverse(
            "federation:shift_signup",
            kwargs={"pk": shift.pk, "guest": self.federated_user.federated_instance.pk},
        )

    def reverse_event_detail(self, event):
        return reverse(
            "federation:event_detail",
            kwargs={"pk": event.pk, "guest": self.federated_user.federated_instance_id},
        )

    @property
    def icon(self):
        title = _("Federated user")
        return mark_safe(
            f'<span class="fa fa-user-tag" data-bs-toggle="tooltip" data-bs-placement="left" title="{title}"></span>'
        )

    class Meta:
        verbose_name = _("federated participant")
        verbose_name_plural = _("federated participants")


class FederatedParticipation(AbstractParticipation):
    federated_user = models.ForeignKey(
        FederatedUser, on_delete=models.CASCADE, verbose_name=_("federated participant")
    )

    def __str__(self):
        return f"{self.federated_user.display_name} @ {self.shift}"

    @property
    def participant(self) -> "AbstractParticipant":
        return self.federated_user.as_participant()

    class Meta:
        verbose_name = _("federated participation")
        verbose_name_plural = _("federated participations")


register_model_for_logging(
    FederatedParticipation,
    PARTICIPATION_LOG_CONFIG,
)
