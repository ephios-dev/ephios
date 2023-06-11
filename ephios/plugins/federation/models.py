import dataclasses

from django.db import models
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from ephios.api.models import AccessToken, Application
from ephios.core.models import AbstractParticipation, Event, Qualification
from ephios.core.signup.participants import AbstractParticipant


class FederatedGuest(models.Model):
    name = models.CharField(max_length=255)
    url = models.URLField()
    access_token = models.ForeignKey(AccessToken, on_delete=models.CASCADE)
    client_id = models.CharField(max_length=255)
    client_secret = models.CharField(max_length=255)


class FederatedHost(models.Model):
    name = models.CharField(max_length=255)
    url = models.URLField()
    access_token = models.CharField(max_length=255)
    oauth_application = models.ForeignKey(Application, on_delete=models.CASCADE)


class InviteCode(models.Model):
    code = models.CharField(max_length=255)
    url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)


class FederatedEventShare(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    shared_with = models.ManyToManyField(FederatedGuest)


class FederatedUser(models.Model):
    email = models.EmailField(_("email address"))
    first_name = models.CharField(_("first name"), max_length=254)
    last_name = models.CharField(_("last name"), max_length=254)
    date_of_birth = models.DateField(_("date of birth"))
    phone = models.CharField(_("phone number"), max_length=254, blank=True)
    qualifications = models.ManyToManyField(Qualification)
    federated_instance = models.ForeignKey(FederatedGuest, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def as_participant(self) -> "FederatedParticipant":
        return FederatedParticipant(
            first_name=self.first_name,
            last_name=self.last_name,
            qualifications=self.qualifications.all(),
            date_of_birth=self.date_of_birth,
            email=self.email,
            federated_user=self,
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
        return reverse("federation:shift_signup", kwargs=dict(pk=shift.pk))

    def reverse_event_detail(self, event):
        return reverse("federation:event_detail", kwargs=dict(pk=event.pk))

    @property
    def icon(self):
        return mark_safe(
            f'<span class="fa fa-user-tag" data-bs-toggle="tooltip" data-bs-placement="left" title="{_("Federated user")}"></span>'
        )


class FederatedParticipation(AbstractParticipation):
    federated_user = models.ForeignKey(
        FederatedUser, on_delete=models.CASCADE, verbose_name=_("federated participant")
    )

    @property
    def participant(self) -> "AbstractParticipant":
        return self.federated_user.as_participant()
