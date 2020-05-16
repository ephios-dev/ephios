from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db.models import (
    EmailField,
    BooleanField,
    CharField,
    DateField,
    IntegerField,
    Model,
    ManyToManyField,
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


class Qualification(Model):
    title = CharField(max_length=254)


class UserProfile(AbstractBaseUser, PermissionsMixin):
    QUALIFICATION_MEDICAL_NONE = 0
    QUALIFICATION_MEDICAL_EH = 1
    QUALIFICATION_MEDICAL_SSD = 2
    QUALIFICATION_MEDICAL_SANH = 3
    QUALIFICATION_MEDICAL_RH = 4
    QUALIFICATION_MEDICAL_RS = 5
    QUALIFICATION_MEDICAL_RA = 6
    QUALIFICATION_MEDICAL_NFS = 7
    QUALIFICATION_MEDICAL_NA = 8
    QUALIFICATION_MEDICAL_OPTIONS = (
        (QUALIFICATION_MEDICAL_NONE, "keine"),
        (QUALIFICATION_MEDICAL_EH, "Ersthelfer"),
        (QUALIFICATION_MEDICAL_SSD, "Schulsanitäter"),
        (QUALIFICATION_MEDICAL_SANH, "Sanitätshelfer"),
        (QUALIFICATION_MEDICAL_RH, "Rettungshelfer"),
        (QUALIFICATION_MEDICAL_RS, "Rettungssanitäter"),
        (QUALIFICATION_MEDICAL_RA, "Rettungsassistent"),
        (QUALIFICATION_MEDICAL_NFS, "Notfallsanitäter"),
        (QUALIFICATION_MEDICAL_NA, "Notarzt"),
    )

    email = EmailField(unique=True, verbose_name="Email address")
    is_active = BooleanField(default=True)
    is_staff = BooleanField(default=False)
    first_name = CharField(max_length=254, verbose_name="First name")
    last_name = CharField(max_length=254, verbose_name="Last name")
    birth_date = DateField()
    phone = IntegerField(null=True)
    medical_qualification = IntegerField(
        choices=QUALIFICATION_MEDICAL_OPTIONS, default=QUALIFICATION_MEDICAL_NONE
    )
    qualifications = ManyToManyField(Qualification)

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
