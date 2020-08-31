import pytz
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import (
    BooleanField,
    CharField,
    DateTimeField,
    ForeignKey,
    IntegerField,
    ManyToManyField,
    Model,
    Q,
    SlugField,
    TextField,
    Manager,
)
from polymorphic.models import PolymorphicModel
from django.utils import dateformat, formats
from jsonfallback.fields import FallbackJSONField
from django.utils.translation import gettext_lazy as _

from jep import settings
from user_management.models import UserProfile


class ActiveManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(active=True)


class EventType(Model):
    title = CharField(_("title"), max_length=254)
    can_grant_qualification = BooleanField(_("can grant qualification"))

    class Meta:
        verbose_name = _("event type")
        verbose_name_plural = _("event types")

    def __str__(self):
        return self.title


class EventSeries(Model):
    pass


class Event(Model):
    title = CharField(_("title"), max_length=254)
    description = TextField(_("description"), blank=True, null=True)
    location = CharField(_("location"), max_length=254)
    type = ForeignKey(EventType, on_delete=models.CASCADE, verbose_name=_("event type"))
    series = ForeignKey(EventSeries, on_delete=models.CASCADE, blank=True, null=True)
    active = BooleanField(default=False)

    objects = ActiveManager()
    all_objects = Manager()

    class Meta:
        verbose_name = _("event")
        verbose_name_plural = _("events")

    @property
    def start_time(self):
        if (first_shift := self.shifts.order_by("start_time").first()) is not None:
            return first_shift.start_time

    @property
    def end_time(self):
        if (last_shift := self.shifts.order_by("end_time").last()) is not None:
            return last_shift.end_time

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("event_management:event_detail", args=[str(self.id)])


class Shift(Model):
    event = ForeignKey(
        Event, on_delete=models.CASCADE, related_name="shifts", verbose_name=_("shifts")
    )
    meeting_time = DateTimeField(_("meeting time"))
    start_time = DateTimeField(_("start time"))
    end_time = DateTimeField(_("end time"))
    signup_method_slug = SlugField(_("signup method"))
    signup_configuration = FallbackJSONField()

    class Meta:
        verbose_name = _("shift")
        verbose_name_plural = _("shifts")

    @property
    def signup_method(self):
        from event_management.signup import signup_method_from_slug

        return signup_method_from_slug(self.signup_method_slug, self)

    def get_start_end_time_display(self):
        tz = pytz.timezone(settings.TIME_ZONE)
        start_time = self.start_time.astimezone(tz)
        return (
            f"{formats.date_format(start_time, 'l')}, {formats.date_format(start_time, 'SHORT_DATE_FORMAT')}, "
            + f"{formats.time_format(start_time)} - {formats.time_format(self.end_time.astimezone(tz))}"
        )

    def get_participations(self, with_state_in=None):
        with_state_in = with_state_in or [AbstractParticipation.CONFIRMED]
        return AbstractParticipation.objects.filter(state__in=with_state_in, shift=self)

    def get_participators(self):
        yield from (
            participation.participator
            for participation in self.get_participations(
                with_state_in=[AbstractParticipation.CONFIRMED]
            )
        )

    def __str__(self):
        return f"{self.event.title} ({self.get_start_end_time_display()})"


class AbstractParticipation(PolymorphicModel):
    REQUESTED = 0
    CONFIRMED = 1
    USER_DECLINED = 2
    RESPONSIBLE_REJECTED = 3
    STATE_CHOICES = (
        (REQUESTED, _("requested")),
        (CONFIRMED, _("confirmed")),
        (USER_DECLINED, _("declined by user")),
        (RESPONSIBLE_REJECTED, _("rejected by responsible")),
    )

    shift = ForeignKey(Shift, on_delete=models.CASCADE, verbose_name=_("shift"))
    state = IntegerField(_("state"), choices=STATE_CHOICES, default=REQUESTED)

    @property
    def participator(self):
        raise NotImplementedError


class LocalParticipation(AbstractParticipation):
    user = ForeignKey(UserProfile, on_delete=models.CASCADE)

    @property
    def participator(self):
        return self.user.as_participator()

    def __str__(self):
        return f"{self.user.get_full_name()} @ {self.shift}"
