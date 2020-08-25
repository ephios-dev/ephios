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
from jsonfallback.fields import FallbackJSONField
from django.utils.translation import gettext as _


class ActiveManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(active=True)


class EventType(Model):
    title = CharField(max_length=254)
    can_grant_qualification = BooleanField()

    def __str__(self):
        return self.title


class EventSeries(Model):
    pass


class Event(Model):
    title = CharField(max_length=254)
    description = TextField(blank=True, null=True)
    location = CharField(max_length=254)
    type = ForeignKey(EventType, on_delete=models.CASCADE)
    series = ForeignKey(EventSeries, on_delete=models.CASCADE, blank=True, null=True)
    active = BooleanField(default=False)

    objects = ActiveManager()
    all_objects = Manager()

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
    event = ForeignKey(Event, on_delete=models.CASCADE, related_name="shifts")
    meeting_time = DateTimeField()
    start_time = DateTimeField()
    end_time = DateTimeField()
    signup_method_slug = SlugField(verbose_name=_("Signup method"))
    signup_configuration = FallbackJSONField()

    @property
    def signup_method(self):
        from event_management.signup import signup_method_from_slug

        return signup_method_from_slug(self.signup_method_slug, self)

    def __str__(self):
        return f"{self.event.title} ({self.start_time}-{self.end_time})"


class AbstractParticipation(Model):
    REQUESTED = 0
    CONFIRMED = 1
    REJECTED = 2
    STATE_CHOICES = (
        (REQUESTED, "requested"),
        (CONFIRMED, "confirmed"),
        (REJECTED, "rejected"),
    )

    shift = ForeignKey(Shift, on_delete=models.CASCADE)
    state = IntegerField(choices=STATE_CHOICES, default=REQUESTED)

    @property
    def participator(self):
        raise NotImplementedError


class LocalParticipation(AbstractParticipation):
    user = ForeignKey(get_user_model(), on_delete=models.CASCADE)

    @property
    def participator(self):
        return self.user.as_participator()

    def __str__(self):
        return f"{self.user.get_full_name()} @ {self.shift}"
