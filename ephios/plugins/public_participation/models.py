import dataclasses
import secrets

from django.db import models
from django.utils.translation import gettext_lazy as _

from ephios.core.models import AbstractParticipation
from ephios.core.signup import AbstractParticipant, Qualification


class PublicUser:
    email = models.EmailField(_("email address"))
    first_name = models.CharField(_("first name"), max_length=254)
    last_name = models.CharField(_("last name"), max_length=254)
    date_of_birth = models.DateField(_("date of birth"))
    phone = models.CharField(_("phone number"), max_length=254, blank=True)
    access_token = models.CharField(
        _("calendar token"), max_length=254, default=secrets.token_urlsafe
    )
    qualifications = models.ManyToManyField(Qualification)

    def as_participant(self) -> AbstractParticipant:
        return PublicUserParticipant(
            first_name=self.first_name,
            last_name=self.last_name,
            qualifications=self.qualifications,
            date_of_birth=self.date_of_birth,
            email=self.email,
            public_user=self,
        )


class PublicParticipation(AbstractParticipation):
    public_user = models.ForeignKey(PublicUser, on_delete=models.CASCADE)

    @property
    def participant(self) -> AbstractParticipant:
        return self.public_user.as_participant()


@dataclasses.dataclass(frozen=True)
class PublicUserParticipant(AbstractParticipant):
    public_user: PublicUser

    def new_participation(self, shift):
        return PublicParticipation(shift=shift, public_user=self.public_user)

    def participation_for(self, shift):
        try:
            return PublicParticipation.objects.get(shift=shift, public_user=self.public_user)
        except PublicParticipation.DoesNotExist:
            return None
