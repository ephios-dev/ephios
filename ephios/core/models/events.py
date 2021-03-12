import functools
import operator
from typing import TYPE_CHECKING

import pytz
from django.conf import settings
from django.db import models, transaction
from django.db.models import (
    BooleanField,
    CharField,
    DateTimeField,
    ForeignKey,
    IntegerField,
    JSONField,
    Manager,
    Model,
    SlugField,
    TextField,
)
from django.utils import formats
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from dynamic_preferences.models import PerInstancePreferenceModel
from guardian.shortcuts import assign_perm
from polymorphic.models import PolymorphicModel

from ephios.extra.json import CustomJSONDecoder, CustomJSONEncoder

if TYPE_CHECKING:
    from ephios.core.models import UserProfile
    from ephios.core.signup import AbstractParticipant, SignupStats


class ActiveManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(active=True)


class EventType(Model):
    title = CharField(_("title"), max_length=254)
    can_grant_qualification = BooleanField(_("can grant qualification"))

    class Meta:
        verbose_name = _("event type")
        verbose_name_plural = _("event types")
        db_table = "eventtype"

    @property
    def color_hex(self):
        return "#FF0"

    def __str__(self):
        return str(self.title)


class Event(Model):
    title = CharField(_("title"), max_length=254)
    description = TextField(_("description"), blank=True, null=True)
    location = CharField(_("location"), max_length=254)
    type = ForeignKey(EventType, on_delete=models.CASCADE, verbose_name=_("event type"))
    active = BooleanField(default=False)

    objects = ActiveManager()
    all_objects = Manager()

    class Meta:
        verbose_name = _("event")
        verbose_name_plural = _("events")
        permissions = [("view_past_event", _("Can view past events"))]
        db_table = "event"

    def get_start_time(self):
        # use shifts.all() in case the shifts have been prefetched
        return min(s.start_time for s in self.shifts.all()) if self.shifts.all() else None

    def get_end_time(self):
        return max(s.end_time for s in self.shifts.all()) if self.shifts.all() else None

    def get_signup_stats(self) -> "SignupStats":
        """Return a SignupStats object aggregated over all shifts of this event, or a default"""
        from ephios.core.signup import SignupStats

        default_for_no_shifts = SignupStats(0, 0, None, None)

        return functools.reduce(
            operator.add,
            [shift.signup_method.get_signup_stats() for shift in self.shifts.all()]
            or [default_for_no_shifts],
        )

    def __str__(self):
        return str(self.title)

    def get_canonical_slug(self):
        return slugify(self.title)

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("core:event_detail", kwargs=dict(pk=self.id, slug=self.get_canonical_slug()))

    def activate(self):
        if not self.active:
            with transaction.atomic():
                self.active = True
                self.full_clean()
                self.save()


class AbstractParticipation(PolymorphicModel):
    class States(models.IntegerChoices):
        REQUESTED = 0, _("requested")
        CONFIRMED = 1, _("confirmed")
        USER_DECLINED = 2, _("declined by user")
        RESPONSIBLE_REJECTED = 3, _("rejected by responsible")
        GETTING_DISPATCHED = 4, _("getting dispatched")

        @classmethod
        def labels_dict(cls):
            return dict(zip(cls.values, cls.labels))

    shift = ForeignKey(
        "Shift", on_delete=models.CASCADE, verbose_name=_("shift"), related_name="participations"
    )
    state = IntegerField(_("state"), choices=States.choices)
    data = models.JSONField(default=dict)

    @property
    def hours_value(self):
        td = self.shift.end_time - self.shift.start_time
        return td.total_seconds() / (60 * 60)

    @property
    def participant(self) -> "AbstractParticipant":
        raise NotImplementedError

    class Meta:
        db_table = "abstractparticipation"

    def __str__(self):
        try:
            return f"{self.participant} @ {self.shift}"
        except NotImplementedError:
            return super().__str__()


class Shift(Model):
    event = ForeignKey(
        Event, on_delete=models.CASCADE, related_name="shifts", verbose_name=_("shifts")
    )
    meeting_time = DateTimeField(_("meeting time"))
    start_time = DateTimeField(_("start time"))
    end_time = DateTimeField(_("end time"))
    signup_method_slug = SlugField(_("signup method"))
    signup_configuration = JSONField(
        default=dict, encoder=CustomJSONEncoder, decoder=CustomJSONDecoder
    )

    class Meta:
        verbose_name = _("shift")
        verbose_name_plural = _("shifts")
        ordering = ("meeting_time", "start_time", "id")
        db_table = "shift"

    @property
    def signup_method(self):
        from ephios.core.signup import signup_method_from_slug

        return signup_method_from_slug(self.signup_method_slug, self)

    def get_start_end_time_display(self):
        tz = pytz.timezone(settings.TIME_ZONE)
        start_time = self.start_time.astimezone(tz)
        return (
            f"{formats.date_format(start_time, 'l')}, {formats.date_format(start_time, 'SHORT_DATE_FORMAT')}, "
            + f"{formats.time_format(start_time)} - {formats.time_format(self.end_time.astimezone(tz))}"
        )

    def get_participants(self, with_state_in=frozenset({AbstractParticipation.States.CONFIRMED})):
        for participation in self.participations.filter(state__in=with_state_in):
            yield participation.participant

    def __str__(self):
        return f"{self.event.title} ({self.get_start_end_time_display()})"


class LocalParticipation(AbstractParticipation):
    user: "UserProfile" = ForeignKey("UserProfile", on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if (
            not self.user.has_perm("core.view_event", obj=self.shift.event)
            and self.state != self.States.GETTING_DISPATCHED
        ):
            # If dispatched by a responsible, the user should be able to view
            # the event, if not already permitted through its group.
            # Currently, this permission does not get removed automatically.
            assign_perm("core.view_event", user_or_group=self.user, obj=self.shift.event)

    @property
    def participant(self):
        return self.user.as_participant()

    class Meta:
        db_table = "localparticipation"


class EventTypePreference(PerInstancePreferenceModel):
    instance = ForeignKey(EventType, on_delete=models.CASCADE)

    class Meta:
        db_table = "eventtypepreference"
        app_label = "core"  # https://github.com/agateblue/django-dynamic-preferences/issues/96
