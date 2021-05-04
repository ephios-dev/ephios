import dataclasses
import secrets

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from ephios.core.models import AbstractParticipation, Event
from ephios.core.models.events import PARTICIPATION_LOG_CONFIG
from ephios.core.signup import AbstractParticipant, Qualification
from ephios.modellogging.log import register_model_for_logging


class EventGuestShare(models.Model):
    event = models.OneToOneField(Event, related_name="guest_share", on_delete=models.CASCADE)
    token = models.CharField(max_length=254, default=secrets.token_urlsafe, unique=True)
    active = models.BooleanField(default=False)

    def new_token(self):
        self.token = secrets.token_urlsafe()

    @property
    def url(self):
        return settings.SITE_URL + reverse(
            "guests:register", kwargs=dict(public_signup_token=self.token, event_id=self.event.id)
        )


class GuestUser(models.Model):
    email = models.EmailField(_("email address"))
    first_name = models.CharField(_("first name"), max_length=254)
    last_name = models.CharField(_("last name"), max_length=254)
    date_of_birth = models.DateField(_("date of birth"))
    phone = models.CharField(_("phone number"), max_length=254, blank=True)
    access_token = models.CharField(max_length=254, default=secrets.token_urlsafe, unique=True)
    qualifications = models.ManyToManyField(Qualification)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def as_participant(self) -> "GuestParticipant":
        return GuestParticipant(
            first_name=self.first_name,
            last_name=self.last_name,
            qualifications=self.qualifications.all(),
            date_of_birth=self.date_of_birth,
            email=self.email,
            guest_user=self,
        )

    def __str__(self):
        return f"{self.first_name} {self.last_name} @ {self.event}"

    class Meta:
        # there might be two people using the same email *sigh*
        unique_together = [["event", "email", "first_name", "last_name"]]


class GuestParticipation(AbstractParticipation):
    guest_user = models.ForeignKey(
        GuestUser, on_delete=models.CASCADE, verbose_name=_("guest participant")
    )

    @property
    def participant(self) -> AbstractParticipant:
        return self.guest_user.as_participant()


register_model_for_logging(GuestParticipation, PARTICIPATION_LOG_CONFIG)


@dataclasses.dataclass(frozen=True)
class GuestParticipant(AbstractParticipant):
    guest_user: GuestUser

    def new_participation(self, shift):
        return GuestParticipation(shift=shift, guest_user=self.guest_user)

    def participation_for(self, shift):
        try:
            return GuestParticipation.objects.get(shift=shift, guest_user=self.guest_user)
        except GuestParticipation.DoesNotExist:
            return None

    def all_participations(self):
        return GuestParticipation.objects.filter(guest_user=self.guest_user)

    def reverse_signup_action(self, shift):
        return reverse(
            "guests:signup_action",
            kwargs=dict(pk=shift.pk, guest_access_token=self.guest_user.access_token),
        )

    def reverse_event_detail(self, event):
        return reverse(
            "guests:event_detail", kwargs=dict(guest_access_token=self.guest_user.access_token)
        )

    @property
    def icon(self):
        return mark_safe(
            f'<span class="fa fa-user-tag" data-toggle="tooltip" data-placement="left" title="{_("Guest")}"></span>'
        )
