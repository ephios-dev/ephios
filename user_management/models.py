from datetime import datetime

import guardian.mixins
from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models import (
    BooleanField,
    CharField,
    DateField,
    EmailField,
    ForeignKey,
    Model,
)
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    def create_user(
        self, email, first_name, last_name, date_of_birth, password=None,
    ):
        user = self.model(
            email=email, first_name=first_name, last_name=last_name, date_of_birth=date_of_birth,
        )
        user.set_password(password)
        user.save()
        return user

    def create_superuser(
        self, email, first_name, last_name, date_of_birth, password=None,
    ):
        user = self.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
        )
        user.is_superuser = True
        user.is_staff = True
        user.save()
        return user


class UserProfile(AbstractBaseUser, PermissionsMixin, guardian.mixins.GuardianUserMixin):
    email = EmailField(_("email address"), unique=True)
    is_active = BooleanField(default=True)
    is_staff = BooleanField(default=False)
    first_name = CharField(_("first name"), max_length=254)
    last_name = CharField(_("last name"), max_length=254)
    date_of_birth = DateField(_("date of birth"))
    phone = CharField(_("phone number"), max_length=254, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = [
        "first_name",
        "last_name",
        "date_of_birth",
    ]

    objects = UserManager()

    class Meta:
        verbose_name = _("user profile")
        verbose_name_plural = _("user profiles")

    def get_full_name(self):
        return self.first_name + " " + self.last_name

    def get_short_name(self):
        return self.first_name

    @property
    def is_minor(self):
        current = datetime.now()
        birthday_upcoming = (
            current.month <= self.date_of_birth.month and current.day < self.date_of_birth.day
        )
        age = (
            current.year - self.date_of_birth.year - 1
            if birthday_upcoming
            else current.year - self.date_of_birth.year
        )
        return age < 18

    def as_participator(self):
        from event_management.signup import LocalUserParticipator

        return LocalUserParticipator(
            first_name=self.first_name,
            last_name=self.last_name,
            qualifications=[],  # TODO
            date_of_birth=self.date_of_birth,
            user=self,
        )


class QualificationTrack(Model):
    title = CharField(_("title"), max_length=254)

    class Meta:
        verbose_name = _("qualification track")
        verbose_name_plural = _("qualification tracks")


class Qualification(Model):
    title = CharField(_("title"), max_length=254)
    track = ForeignKey(
        QualificationTrack, on_delete=models.CASCADE, verbose_name=_("qualification track")
    )

    class Meta:
        verbose_name = _("qualification")
        verbose_name_plural = _("qualifications")

    def __str__(self):
        return self.title


class QualificationGrant(Model):
    qualification = ForeignKey(
        Qualification, on_delete=models.CASCADE, verbose_name=_("qualification")
    )
    user = ForeignKey(get_user_model(), on_delete=models.CASCADE, verbose_name=_("user profile"))
    expiration_date = DateField(_("expiration date"), blank=True, null=True)
