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
)
from jsonfallback.fields import FallbackJSONField


class EventType(Model):
    title = CharField(max_length=254)
    can_grant_qualification = BooleanField()

    def __str__(self):
        return self.title


class Event(Model):
    title = CharField(max_length=254)
    description = TextField(blank=True, null=True)
    location = CharField(max_length=254)
    type = ForeignKey(EventType, on_delete=models.CASCADE)

    @property
    def start_time(self):
        return self.shift_set.order_by("start_time").first().start_time

    @property
    def end_time(self):
        last_shift = self.shift_set.order_by("-start_time").first().start_time
        return last_shift if last_shift.day > self.start_time.day else None

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("event_management:event_detail", args=[str(self.id)])


class EventSeries(Model):
    events = ManyToManyField(Event)


class Shift(Model):
    event = ForeignKey(Event, on_delete=models.CASCADE)
    meeting_time = DateTimeField()
    start_time = DateTimeField()
    end_time = DateTimeField()
    signup_method_slug = SlugField()
    signup_configuration = FallbackJSONField()

    @property
    def signup_method(self):
        from event_management.signup import register_signup_method

        for receiver, method in register_signup_method.send(None):
            if method.slug == self.signup_method_slug:
                return method(self)
        raise ValueError(f"Signup Method '{self.signup_method_slug}' was not found.")

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


class LocalParticipation(AbstractParticipation):
    user = ForeignKey(get_user_model(), on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.get_full_name()} @ {self.shift}"
