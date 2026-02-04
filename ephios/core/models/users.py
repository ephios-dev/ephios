import datetime
import functools
import secrets
import uuid
from datetime import date
from itertools import chain
from typing import Optional

import guardian.mixins
from django.conf import settings
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
    JSONField,
    Max,
    Model,
    Q,
    Sum,
    UniqueConstraint,
    Value,
)
from django.db.models.functions import Lower, TruncDate
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from polymorphic.models import PolymorphicModel

from ephios.extra.fields import EndOfDayDateTimeField
from ephios.extra.json import CustomJSONDecoder, CustomJSONEncoder
from ephios.extra.widgets import CustomDateInput
from ephios.modellogging.log import (
    ModelFieldsLogConfig,
    add_log_recorder,
    dont_log,
    log,
    register_model_for_logging,
)
from ephios.modellogging.recorders import FixedMessageLogRecorder, M2MLogRecorder


class UserProfileQuerySet(models.QuerySet):
    def visible(self):
        return self.filter(is_visible=True)


class UserProfileManager(BaseUserManager):
    def create_user(
        self,
        email,
        display_name,
        date_of_birth,
        password=None,
    ):
        # pylint: disable=unexpected-keyword-arg,no-value-for-parameter
        user = self.model(
            email=email,
            display_name=display_name,
            date_of_birth=date_of_birth,
        )
        user.set_password(password)
        user.save()
        return user

    def create_superuser(
        self,
        email,
        display_name,
        date_of_birth,
        password=None,
    ):
        with transaction.atomic():
            user = self.create_user(
                email=email,
                password=password,
                display_name=display_name,
                date_of_birth=date_of_birth,
            )
            user.is_superuser = True
            user.is_staff = True
            user.save()
            return user

    def get_by_natural_key(self, username):
        # postgres uses case-sensitive collations, so we need to use iexact here
        return self.get(**{f"{self.model.USERNAME_FIELD}__iexact": username})


class VisibleUserProfileManager(BaseUserManager):
    def get_queryset(self):
        return super().get_queryset().visible()


class UserProfile(guardian.mixins.GuardianUserMixin, PermissionsMixin, AbstractBaseUser):
    email = EmailField(_("email address"), unique=True)
    email_invalid = BooleanField(default=False, verbose_name=_("Email address invalid"))
    is_active = BooleanField(default=True, verbose_name=_("Active"))
    is_visible = BooleanField(default=True, verbose_name=_("Visible"))
    is_staff = BooleanField(
        default=False,
        verbose_name=_("Administrator"),
    )
    display_name = CharField(_("name"), max_length=254)
    date_of_birth = DateField(_("date of birth"), null=True, blank=True)
    phone = CharField(_("phone number"), max_length=254, blank=True, null=True)
    calendar_token = CharField(_("calendar token"), max_length=254, default=secrets.token_urlsafe)
    preferred_language = CharField(
        _("preferred language"),
        max_length=10,
        default=settings.LANGUAGE_CODE,
        choices=settings.LANGUAGES,
    )
    disabled_notifications = JSONField(
        default=list, encoder=CustomJSONEncoder, decoder=CustomJSONDecoder
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = [
        "display_name",
        "date_of_birth",
    ]

    objects = VisibleUserProfileManager.from_queryset(UserProfileQuerySet)()
    all_objects = UserProfileManager.from_queryset(UserProfileQuerySet)()

    class Meta:
        verbose_name = _("user profile")
        verbose_name_plural = _("user profiles")
        db_table = "userprofile"
        base_manager_name = "all_objects"
        default_manager_name = "all_objects"

        constraints = [
            UniqueConstraint(
                Lower("email"),
                name="user_email_ci_uniqueness",
                violation_error_message=_("User profile with this email address already exists."),
                # we want to allow case insensitive signin, so we need to ensure that the email is unique in all cases
            ),
        ]

    def get_full_name(self):
        return self.display_name

    def reset_calendar_token(self):
        self.calendar_token = secrets.token_urlsafe()
        self.save(update_fields=["calendar_token"])

    def __str__(self):
        return str(self.get_full_name())

    @property
    def age(self) -> Optional[int]:
        if self.date_of_birth is None:
            return None
        today, born = date.today(), self.date_of_birth
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    @property
    def is_minor(self):
        return self.date_of_birth is not None and self.age < 18

    def as_participant(self):
        from ephios.core.signup.participants import LocalUserParticipant

        return LocalUserParticipant(
            display_name=self.display_name,
            qualifications=self.qualifications,
            date_of_birth=self.date_of_birth,
            email=self.email if self.is_active else None,
            user=self,
        )

    @property
    def qualifications(self):
        """
        Returns a queryset with all qualifications that are granted to this user and not expired.
        Be careful to not use this in a loop, as it will perform a query for each iteration.
        """
        return (
            Qualification.objects.filter(
                pk__in=self.qualification_grants.unexpired().values_list(
                    "qualification_id", flat=True
                )
            )
            .annotate(
                expires=Max(F("grants__expires"), filter=Q(grants__user=self)),
            )
            .select_related("category")
        )

    def get_workhour_items(self):
        from ephios.core.models import AbstractParticipation

        participations = (
            self.participations.filter(state=AbstractParticipation.States.CONFIRMED)
            .annotate(
                duration=ExpressionWrapper(
                    (F("end_time") - F("start_time")),
                    output_field=models.DurationField(),
                ),
                date=ExpressionWrapper(TruncDate(F("start_time")), output_field=DateField()),
                reason=F("shift__event__title"),
                type=Value("event"),
                origin_id=F("shift__event__pk"),
            )
            .values("duration", "date", "reason", "type", "origin_id")
        )
        workinghours = self.workinghours_set.annotate(
            duration=F("hours"), type=Value("request"), origin_id=F("pk")
        ).values("duration", "date", "reason", "type", "origin_id")
        hour_sum = (
            participations.aggregate(Sum("duration"))["duration__sum"] or datetime.timedelta()
        ) + datetime.timedelta(
            hours=float(workinghours.aggregate(Sum("duration"))["duration__sum"] or 0)
        )
        return hour_sum, list(
            sorted(chain(participations, workinghours), key=lambda k: k["date"], reverse=True)
        )


register_model_for_logging(
    UserProfile,
    ModelFieldsLogConfig(
        unlogged_fields={"id", "password", "calendar_token", "last_login", "user_permissions"},
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


class QualificationCategoryManager(models.Manager):
    def get_by_natural_key(self, category_uuid, *args):
        return self.get(uuid=category_uuid)


@log()
class QualificationCategory(Model):
    uuid = models.UUIDField("UUID", unique=True, default=uuid.uuid4)
    title = CharField(_("title"), max_length=254)
    show_with_user = BooleanField(
        default=True,
        verbose_name=_("Show qualifications of this category everywhere a user is presented"),
    )

    objects = QualificationCategoryManager()

    class Meta:
        verbose_name = _("qualification category")
        verbose_name_plural = _("qualification categories")
        db_table = "qualificationcategory"

    def __str__(self):
        return str(self.title)

    def natural_key(self):
        return (self.uuid, self.title)


class QualificationManager(models.Manager):
    def get_by_natural_key(self, qualification_uuid, *args):
        return self.get(uuid=qualification_uuid)


class Qualification(Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, verbose_name="UUID")
    title = CharField(_("title"), max_length=254)
    abbreviation = CharField(max_length=254, verbose_name=_("Abbreviation"))
    category = ForeignKey(
        QualificationCategory,
        on_delete=models.CASCADE,
        related_name="qualifications",
        verbose_name=_("category"),
    )
    includes = models.ManyToManyField(
        "self",
        related_name="included_by",
        verbose_name=_("Included"),
        help_text=_("other qualifications that this qualification includes"),
        symmetrical=False,
        blank=True,
    )
    is_imported = models.BooleanField(verbose_name=_("imported"), default=True)

    objects = QualificationManager()

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

    def natural_key(self):
        return (self.uuid, self.title)

    natural_key.dependencies = ["core.QualificationCategory"]


register_model_for_logging(
    Qualification,
    ModelFieldsLogConfig(),
)


class CustomQualificationGrantQuerySet(models.QuerySet):
    # Available on both Manager and QuerySet.
    def unexpired(self):
        return self.exclude(expires__isnull=False, expires__lt=timezone.now())


class ExpirationDateField(models.DateTimeField):
    """
    A model datetime field whose formfield is an EndOfDayDateTimeField
    """

    def formfield(self, **kwargs):
        return super().formfield(
            **{
                "widget": CustomDateInput,
                "form_class": EndOfDayDateTimeField,
                **kwargs,
            }
        )


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
    expires = ExpirationDateField(_("expiration date"), blank=True, null=True)
    externally_managed = models.BooleanField(
        verbose_name=_("externally managed"),
        default=False,
        help_text=_("The qualification was granted by an external system."),
    )

    objects = CustomQualificationGrantQuerySet.as_manager()

    def is_expired(self):
        return self.expires and self.expires < timezone.now()

    def is_valid(self):
        return not self.is_expired()

    def __str__(self):
        template = _("{qualification} for {user}")
        return template.format(qualification=str(self.qualification), user=str(self.user))

    class Meta:
        unique_together = [["qualification", "user"]]  # issue #218
        db_table = "qualificationgrant"
        verbose_name = _("Qualification grant")
        verbose_name_plural = _("Qualification grants")


register_model_for_logging(
    QualificationGrant,
    ModelFieldsLogConfig(attach_to_func=lambda grant: (UserProfile, grant.user_id)),
)


@dont_log  # as we log the specific models
class AbstractConsequence(PolymorphicModel):
    slug = models.CharField(max_length=255)
    data = models.JSONField(default=dict, encoder=CustomJSONEncoder, decoder=CustomJSONDecoder)

    class States(models.TextChoices):
        NEEDS_CONFIRMATION = "needs_confirmation", _("needs confirmation")
        CONFIRMED = "confirmed", _("confirmed")
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
        db_table = "abstractconsequence"
        verbose_name = _("Abstract consequence")
        verbose_name_plural = _("Abstract consequences")

    @classmethod
    def filter_editable_by_user(cls, handler, user):
        raise NotImplementedError

    @property
    def handler(self):
        from ephios.core import consequences

        return consequences.consequence_handler_from_slug(self.slug)

    def confirm(self):
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
                from ephios.core.services.notifications.types import ConsequenceApprovedNotification

                ConsequenceApprovedNotification.send(self)
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

    def deny(self):
        from ephios.core.consequences import ConsequenceError

        if self.state not in {self.States.NEEDS_CONFIRMATION, self.States.FAILED}:
            raise ConsequenceError(_("Consequence was executed or denied already."))
        self.state = self.States.DENIED
        self.save()
        from ephios.core.services.notifications.types import ConsequenceDeniedNotification

        ConsequenceDeniedNotification.send(self)

    def render(self):
        return f"{self.participant_display_name()} {self.handler.render(self)}"

    def __str__(self):
        return self.render()

    def participant_display_name(self):
        raise NotImplementedError

    def attach_log_to_object(self):
        return AbstractConsequence, self.id


class LocalConsequence(AbstractConsequence):
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        verbose_name=_("affected user"),
        null=True,
        related_name="affecting_consequences",
    )

    class Meta:
        db_table = "localconsequence"
        verbose_name = _("Local consequence")
        verbose_name_plural = _("Local consequences")

    @classmethod
    def filter_editable_by_user(cls, handler, user):
        return handler.filter_editable_by_user(user)

    def participant_display_name(self):
        return self.user.display_name

    def attach_log_to_object(self):
        return UserProfile, self.user_id


# register_model_for_logging(
#     LocalConsequence,
#     ModelFieldsLogConfig(
#         unlogged_fields=["id", "slug", "user", "data"],
#         attach_to_func=lambda consequence: consequence.attach_log_to_object(),
#     ),
# )


@log()
class WorkingHours(Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, verbose_name=_("User"))
    hours = models.DecimalField(decimal_places=2, max_digits=7, verbose_name=_("Hours of work"))
    reason = models.CharField(max_length=1024, default="", verbose_name=_("Occasion"))
    date = models.DateField(verbose_name=_("Date"))

    class Meta:
        db_table = "workinghours"
        verbose_name = _("Working hours")
        verbose_name_plural = _("Working hours")

    def __str__(self):
        return f"{self.hours} hours for {self.user} because of {self.reason} on {self.date}"


@dont_log
class Notification(Model):
    slug = models.SlugField(max_length=255)
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        verbose_name=_("affected user"),
        null=True,
    )
    read = models.BooleanField(default=False, verbose_name=_("read"))
    processing_completed = models.BooleanField(
        default=False,
        verbose_name=_("processing completed"),
        help_text=_(
            "All enabled notification backends have processed this notification when flag is set"
        ),
    )
    processed_by = models.JSONField(
        blank=True,
        default=list,
        encoder=CustomJSONEncoder,
        decoder=CustomJSONDecoder,
        help_text=_("List of slugs of notification backends that have processed this notification"),
    )
    data = models.JSONField(
        blank=True, default=dict, encoder=CustomJSONEncoder, decoder=CustomJSONDecoder
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @functools.cached_property
    def notification_type(self):
        from ephios.core.services.notifications.types import notification_type_from_slug

        return notification_type_from_slug(self.slug)

    @property
    def subject(self):
        """The subject of the notification."""
        return self.notification_type.get_subject(self)

    @property
    def body(self):
        """The body text of the notification."""
        return self.notification_type.get_body(self)

    @property
    def is_obsolete(self):
        return self.notification_type.is_obsolete(self)

    def __str__(self):
        return _("{subject} for {user}").format(subject=self.subject, user=self.user or _("Guest"))

    def __repr__(self):
        return f"Notification(user={self.user!r}, slug={self.notification_type.slug}, data={self.data!r})"

    def as_html(self):
        """The notification rendered as HTML."""
        return self.notification_type.as_html(self)

    def as_plaintext(self):
        """The notification rendered as plaintext."""
        return self.notification_type.as_plaintext(self)

    def get_actions(self):
        return self.notification_type.get_actions_with_referrer(self)


@log(ModelFieldsLogConfig(unlogged_fields={"id"}, redacted_fields={"client_secret"}))
class IdentityProvider(Model):
    internal_name = models.CharField(
        max_length=255,
        verbose_name=_("internal name"),
        help_text=_("Internal name for this provider."),
        unique=True,
    )
    label = models.CharField(
        max_length=255,
        verbose_name=_("label"),
        help_text=_("The label displayed to users attempting to log in with this provider."),
    )
    client_id = models.CharField(
        max_length=255,
        verbose_name=_("client id"),
        help_text=_("Your client id provided by the OIDC provider."),
    )
    client_secret = models.CharField(
        max_length=255,
        verbose_name=_("client secret"),
        help_text=_("Your client secret provided by the OIDC provider."),
    )
    scopes = models.CharField(
        max_length=255,
        default="openid profile email",
        verbose_name=_("scopes"),
        help_text=_(
            "The OIDC scopes to request from the provider. Separate multiple scopes with spaces. Use the default value if you are unsure."
        ),
    )
    authorization_endpoint = models.URLField(
        verbose_name=_("authorization endpoint"), help_text=_("The OIDC authorization endpoint.")
    )
    token_endpoint = models.URLField(
        verbose_name=_("token endpoint"), help_text=_("The OIDC token endpoint.")
    )
    userinfo_endpoint = models.URLField(
        verbose_name=_("user endpoint"), help_text=_("The OIDC user endpoint.")
    )
    end_session_endpoint = models.URLField(
        blank=True,
        null=True,
        verbose_name=_("end session endpoint"),
        help_text=_("The OIDC end session endpoint, if supported by your provider."),
    )
    jwks_uri = models.URLField(
        blank=True,
        null=True,
        verbose_name=_("JWKS endpoint"),
        help_text=_(
            "The OIDC JWKS endpoint. A less secure signing method will be used if this is not provided."
        ),
    )
    default_groups = models.ManyToManyField(
        Group,
        blank=True,
        verbose_name=_("default groups"),
        help_text=_("The groups that users logging in with this provider will be added to."),
    )
    group_claim = models.CharField(
        max_length=254,
        blank=True,
        verbose_name=_("group claim"),
        help_text=_(
            "The name of the claim that contains the user's groups. "
            "Leave empty if your provider does not support this. You can use dot notation to access nested claims."
        ),
    )
    create_missing_groups = models.BooleanField(
        default=False,
        verbose_name=_("create missing groups"),
        help_text=_(
            "If enabled, groups from the claim defined above that do not exist yet will be created automatically."
        ),
    )
    qualification_claim = models.CharField(
        max_length=254,
        blank=True,
        verbose_name=_("qualification claim"),
        help_text=_(
            "The name of the claim that contains the user's qualifications. "
            "Leave empty if your provider does not support this. You can use dot notation to access nested claims. "
            "Granted qualifications not found in the claim will be removed from the user on login."
        ),
    )
    qualification_codename_to_uuid = models.JSONField(
        verbose_name=_("qualification codename to uuid"),
        help_text=_(
            "A json encoded dictionary containing mappings of qualification names as they appear in the"
            "qualification claim to the qualification uuid. If a key is not found, use the key directly."
        ),
        default=dict,
        blank=True,
    )

    def __str__(self):
        return _("Identity provider {label}").format(label=self.label)

    class Meta:
        verbose_name = _("Identity provider")
        verbose_name_plural = _("Identity providers")
