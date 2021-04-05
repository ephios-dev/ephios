import functools
import secrets
import uuid
from datetime import date
from itertools import chain

import guardian.mixins
from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import Group, PermissionsMixin
from django.db import models, transaction
from django.db.models import (
    BooleanField,
    CharField,
    DateField,
    EmailField,
    ExpressionWrapper,
    F,
    ForeignKey,
    Max,
    Model,
    Q,
    Sum,
)
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from ephios.extra.json import CustomJSONDecoder, CustomJSONEncoder
from ephios.modellogging.log import (
    ModelFieldsLogConfig,
    add_log_recorder,
    register_model_for_logging,
)
from ephios.modellogging.recorders import FixedMessageLogRecorder, M2MLogRecorder


class UserProfileManager(BaseUserManager):
    def create_user(
        self,
        email,
        first_name,
        last_name,
        date_of_birth,
        password=None,
    ):
        # pylint: disable=unexpected-keyword-arg,no-value-for-parameter
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


class UserProfile(guardian.mixins.GuardianUserMixin, PermissionsMixin, AbstractBaseUser):
    email = EmailField(_("email address"), unique=True)
    is_active = BooleanField(default=True, verbose_name=_("Active"))
    is_staff = BooleanField(default=False, verbose_name=_("Staff user"))
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

    objects = UserProfileManager()

    class Meta:
        verbose_name = _("user profile")
        verbose_name_plural = _("user profiles")
        db_table = "userprofile"

    def get_full_name(self):
        return self.first_name + " " + self.last_name

    def __str__(self):
        return self.get_full_name()

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
        from ephios.core.signup import LocalUserParticipant

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
        return Qualification.objects.filter(
            pk__in=self.qualification_grants.filter(
                Q(expires__gt=timezone.now()) | Q(expires__isnull=True)
            ).values_list("qualification_id", flat=True)
        ).annotate(
            expires=Max(F("grants__expires"), filter=Q(grants__user=self)),
        )

    def get_shifts(self, with_participation_state_in):
        from ephios.core.models import Shift

        shift_ids = self.localparticipation_set.filter(
            state__in=with_participation_state_in
        ).values_list("shift", flat=True)
        return Shift.objects.filter(pk__in=shift_ids).select_related("event")

    def get_workhour_items(self):
        from ephios.core.models import AbstractParticipation

        participation = (
            self.localparticipation_set.filter(state=AbstractParticipation.States.CONFIRMED)
            .annotate(
                hours=ExpressionWrapper(
                    (
                        F("shift__end_time") - F("shift__start_time")
                    )  # calculate length of shift in μs
                    / 1000000  # convert microseconds to seconds
                    / 3600,  # convert seconds to hours
                    output_field=models.DecimalField(),
                ),
                date=ExpressionWrapper(TruncDate(F("shift__start_time")), output_field=DateField()),
                reason=F("shift__event__title"),
            )
            .values("hours", "date", "reason")
        )
        workinghours = self.workinghours_set.all().values("hours", "date", "reason")
        hour_sum = (participation.aggregate(Sum("hours"))["hours__sum"] or 0) + (
            workinghours.aggregate(Sum("hours"))["hours__sum"] or 0
        )
        return hour_sum, list(sorted(chain(participation, workinghours), key=lambda k: k["date"]))


register_model_for_logging(
    UserProfile,
    ModelFieldsLogConfig(
        unlogged_fields={"id", "password", "calendar_token", "last_login"},
    ),
)


register_model_for_logging(
    Group,
    ModelFieldsLogConfig(
        unlogged_fields={"id", "permissions"},
        initial_recorders_func=lambda group: [
            M2MLogRecorder(UserProfile.groups.field, reverse=True, verbose_name=_("Users")),
        ],
    ),
)


class QualificationCategory(Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4)
    title = CharField(_("title"), max_length=254)

    class Meta:
        verbose_name = _("qualification track")
        verbose_name_plural = _("qualification tracks")
        db_table = "qualificationcategory"

    def __str__(self):
        return str(self.title)


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
        db_table = "qualification"

    def __str__(self):
        return str(self.title)


class QualificationGrant(Model):
    qualification = ForeignKey(
        Qualification,
        on_delete=models.CASCADE,
        verbose_name=_("qualification"),
        related_name="grants",
    )
    user = ForeignKey(
        get_user_model(),
        related_name="qualification_grants",
        on_delete=models.CASCADE,
        verbose_name=_("user profile"),
    )
    expires = models.DateTimeField(_("expiration date"), blank=True, null=True)

    def __str__(self):
        return f"{self.qualification!s} {_('for')} {self.user!s}"

    class Meta:
        unique_together = [["qualification", "user"]]  # issue #218
        db_table = "qualificationgrant"
        verbose_name = _("Qualification grant")


register_model_for_logging(
    QualificationGrant,
    ModelFieldsLogConfig(attach_to_func=lambda grant: (UserProfile, grant.user_id)),
)


class Consequence(Model):
    slug = models.CharField(max_length=255)
    data = models.JSONField(default=dict, encoder=CustomJSONEncoder, decoder=CustomJSONDecoder)

    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        verbose_name=_("affected user"),
        null=True,
        related_name="affecting_consequences",
    )

    class States(models.TextChoices):
        NEEDS_CONFIRMATION = "needs_confirmation", _("needs confirmation")
        EXECUTED = "executed", _("executed")
        FAILED = "failed", _("failed")
        DENIED = "denied", _("denied")

    state = models.TextField(
        max_length=31,
        choices=States.choices,
        default=States.NEEDS_CONFIRMATION,
        verbose_name=_("State"),
    )

    class Meta:
        db_table = "consequence"
        verbose_name = _("Consequence")

    @property
    def handler(self):
        from ephios.core import consequences

        return consequences.consequence_handler_from_slug(self.slug)

    def confirm(self, user):
        from ephios.core.consequences import ConsequenceError

        if self.state not in {
            self.States.NEEDS_CONFIRMATION,
            self.States.DENIED,
            self.States.FAILED,
        }:
            raise ConsequenceError(_("Consequence was executed already."))

        try:
            with transaction.atomic():
                self.handler.execute(self)
        except Exception as e:  # pylint: disable=broad-except
            self.state = self.States.FAILED
            add_log_recorder(
                self,
                FixedMessageLogRecorder(
                    label=_("Reason"),
                    message=str(e),
                ),
            )
            raise ConsequenceError(str(e)) from e
        else:
            self.state = self.States.EXECUTED
        finally:
            self.save()

    def deny(self, user):
        from ephios.core.consequences import ConsequenceError

        if self.state not in {self.States.NEEDS_CONFIRMATION, self.States.FAILED}:
            raise ConsequenceError(_("Consequence was executed or denied already."))
        self.state = self.States.DENIED
        self.save()

    def render(self):
        return self.handler.render(self)

    def __str__(self):
        return self.render()

    def attach_log_to_object(self):
        if self.user_id:
            return UserProfile, self.user_id
        return Consequence, self.id


register_model_for_logging(
    Consequence,
    ModelFieldsLogConfig(
        unlogged_fields=["id", "slug", "user", "data"],
        attach_to_func=lambda consequence: consequence.attach_log_to_object(),
    ),
)


class WorkingHours(Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    hours = models.DecimalField(decimal_places=2, max_digits=7)
    reason = models.CharField(max_length=1024, default="")
    date = models.DateField()

    class Meta:
        db_table = "workinghours"


class Notification(Model):
    slug = models.SlugField(max_length=255)
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        verbose_name=_("affected user"),
        null=True,
    )
    failed = models.BooleanField(default=False)
    data = models.JSONField(
        blank=True, default=dict, encoder=CustomJSONEncoder, decoder=CustomJSONDecoder
    )

    @functools.cached_property
    def notification_type(self):
        from ephios.core.services.notifications.types import notification_type_from_slug

        return notification_type_from_slug(self.slug)

    @property
    def subject(self):
        return self.notification_type.get_subject(self)

    def as_plaintext(self):
        return self.notification_type.as_plaintext(self)

    def as_html(self):
        return self.notification_type.as_html(self)
