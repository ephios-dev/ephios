import secrets
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
    Exists,
    OuterRef,
)
from django.utils import timezone


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
    email = EmailField(unique=True, verbose_name="Email address")
    is_active = BooleanField(default=True)
    is_staff = BooleanField(default=False)
    first_name = CharField(max_length=254, verbose_name="First name")
    last_name = CharField(max_length=254, verbose_name="Last name")
    date_of_birth = DateField()
    phone = CharField(max_length=254, null=True, blank=True)
    calendar_token = CharField(max_length=254, default=secrets.token_urlsafe)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = [
        "first_name",
        "last_name",
        "date_of_birth",
    ]

    objects = UserManager()

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

    @property
    def qualifications(self):
        return Qualification.objects.annotate(
            active_grant=Exists(
                QualificationGrant.objects.filter(
                    user__eq=self, expires__lt=timezone.now(), qualification=OuterRef("pk")
                )
            )
        ).filter(active_grant=True)

    def get_shifts(self, with_participation_state_in):
        from event_management.models import Shift

        shift_ids = self.localparticipation_set.filter(
            state__in=with_participation_state_in
        ).values_list("shift", flat=True)
        return Shift.objects.filter(pk__in=shift_ids)


class QualificationCategory(Model):
    uuid = models.UUIDField(unique=True)
    title = CharField(max_length=254)


class Qualification(Model):
    uuid = models.UUIDField(unique=True)
    title = CharField(max_length=254)
    abbreviation = CharField(max_length=254)
    category = ForeignKey(
        QualificationCategory, on_delete=models.CASCADE, related_name="qualifications"
    )
    included_qualifications = models.ManyToManyField(
        "self", related_name="included_in_set", symmetrical=False
    )

    def includes(self, other):
        # FIXME make this faster by using a cache or something
        if self == other:
            return True
        return any(
            included_qualification.includes(other)
            for included_qualification in self.included_qualifications.all()
        )

    def __eq__(self, other):
        return self.uuid == other.uuid

    def __hash__(self):
        return hash(self.uuid)

    def __str__(self):
        return self.title


class QualificationGrant(Model):
    qualification = ForeignKey(Qualification, on_delete=models.CASCADE, related_name="grants")
    user = ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="qualification_grants"
    )
    expires = models.DateTimeField(blank=True, null=True)
