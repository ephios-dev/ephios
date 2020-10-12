import secrets
import uuid
from datetime import date, datetime

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
    Exists,
    F,
    ForeignKey,
    Max,
    Model,
    OuterRef,
    Q,
)
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    def create_user(
        self,
        email,
        first_name,
        last_name,
        date_of_birth,
        password=None,
    ):
        user = self.model(
            email=email,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
        )
        user.set_password(password)
        user.save()
        return user

    def create_superuser(
        self,
        email,
        first_name,
        last_name,
        date_of_birth,
        password=None,
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
    phone = CharField(_("phone number"), max_length=254, blank=True)
    calendar_token = CharField(_("calendar token"), max_length=254, default=secrets.token_urlsafe)

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
    def age(self):
        today, born = date.today(), self.date_of_birth
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    @property
    def is_minor(self):
        return self.age < 18

    def as_participant(self):
        from ephios.event_management.signup import LocalUserParticipant

        return LocalUserParticipant(
            first_name=self.first_name,
            last_name=self.last_name,
            qualifications=self.qualifications,
            date_of_birth=self.date_of_birth,
            email=self.email if self.is_active else None,
            user=self,
        )

    @property
    def qualifications(self):
        return Qualification.objects.annotate(
            has_active_grant=Exists(
                QualificationGrant.objects.filter(user=self, qualification=OuterRef("pk")).filter(
                    Q(expires__gt=timezone.now()) | Q(expires__isnull=True)
                )
            ),
            expires=Max(F("grants__expires")),
        ).filter(has_active_grant=True)

    def get_shifts(self, with_participation_state_in):
        from ephios.event_management.models import Shift

        shift_ids = self.localparticipation_set.filter(
            state__in=with_participation_state_in
        ).values_list("shift", flat=True)
        return Shift.objects.filter(pk__in=shift_ids)


class QualificationCategory(Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4)
    title = CharField(_("title"), max_length=254)

    class Meta:
        verbose_name = _("qualification track")
        verbose_name_plural = _("qualification tracks")

    def __str__(self):
        return self.title


class Qualification(Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4)
    title = CharField(_("title"), max_length=254)
    abbreviation = CharField(max_length=254)
    category = ForeignKey(
        QualificationCategory,
        on_delete=models.CASCADE,
        related_name="qualifications",
        verbose_name=_("category"),
    )
    included_qualifications = models.ManyToManyField(
        "self", related_name="included_by", symmetrical=False, blank=True
    )

    def __eq__(self, other):
        return self.uuid == other.uuid if other else False

    def __hash__(self):
        return hash(self.uuid)

    class Meta:
        verbose_name = _("qualification")
        verbose_name_plural = _("qualifications")

    def __str__(self):
        return self.title


class QualificationGrant(Model):
    qualification = ForeignKey(
        Qualification,
        on_delete=models.CASCADE,
        verbose_name=_("qualification"),
        related_name="grants",
    )
    user = ForeignKey(get_user_model(), on_delete=models.CASCADE, verbose_name=_("user profile"))
    expires = models.DateTimeField(_("expiration date"), blank=True, null=True)

    def __str__(self):
        return f"{self.qualification!s}, {self.user!s}"
