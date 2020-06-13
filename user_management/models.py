from datetime import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models import (
    EmailField,
    BooleanField,
    CharField,
    DateField,
    IntegerField,
    Model,
    ManyToManyField, ForeignKey,
)


class UserManager(BaseUserManager):
    def create_user(
        self, email, first_name, last_name, birth_date, password=None,
    ):
        user = self.model(
            email=email,
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date,
        )
        user.set_password(password)
        user.save()
        return user

    def create_superuser(
        self, email, first_name, last_name, birth_date, password=None,
    ):
        user = self.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date,
        )
        user.is_superuser = True
        user.is_staff = True
        user.save()
        return user


class UserProfile(AbstractBaseUser, PermissionsMixin):
    email = EmailField(unique=True, verbose_name="Email address")
    is_active = BooleanField(default=True)
    is_staff = BooleanField(default=False)
    first_name = CharField(max_length=254, verbose_name="First name")
    last_name = CharField(max_length=254, verbose_name="Last name")
    birth_date = DateField()
    phone = IntegerField(null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = [
        "first_name",
        "last_name",
        "birth_date",
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
            current.month <= self.birth_date.month and current.day < self.birth_date.day
        )
        age = (
            current.year - self.birth_date.year - 1
            if birthday_upcoming
            else current.year - self.birth_date.year
        )
        return age < 18


class QualificationTrack(Model):
    title = CharField(max_length=254)


class Qualification(Model):
    title = CharField(max_length=254)
    track = ForeignKey(QualificationTrack, on_delete=models.CASCADE)

    def __str__(self):
        return self.title


class QualificationGrant(Model):
    qualification = ForeignKey(Qualification, on_delete=models.CASCADE)
    user = ForeignKey(get_user_model(), on_delete=models.CASCADE)
    expriation_date = DateField(blank=True, null=True)