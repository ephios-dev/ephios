import dataclasses
import functools
from datetime import date
from typing import Optional

from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from ephios.core.models import AbstractParticipation, LocalParticipation, Qualification
from ephios.core.models.events import PlaceholderParticipation


@dataclasses.dataclass(frozen=True)
class AbstractParticipant:
    first_name: str
    last_name: str
    qualifications: QuerySet = dataclasses.field(hash=False)
    date_of_birth: Optional[date]
    email: Optional[str]  # if set to None, no notifications are sent

    def get_age(self, today: date = None):
        if self.date_of_birth is None:
            return None
        today, born = today or date.today(), self.date_of_birth
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    @property
    def is_minor(self):
        if age := self.get_age():
            return age < 18
        return False

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def new_participation(self, shift):
        raise NotImplementedError

    def participation_for(self, shift):
        """Return the participation object for a shift. Return None if it does not exist."""
        raise NotImplementedError

    def all_participations(self):
        """Return all participations for this participant"""
        raise NotImplementedError

    @functools.lru_cache(maxsize=64)
    def collect_all_qualifications(self) -> set:
        return Qualification.collect_all_included_qualifications(self.qualifications)

    def has_qualifications(self, qualifications):
        return set(qualifications) <= self.collect_all_qualifications()

    def reverse_signup_action(self, shift):
        raise NotImplementedError

    def reverse_event_detail(self, event):
        raise NotImplementedError

    @property
    def icon(self):
        return mark_safe('<span class="fa fa-user"></span>')


@dataclasses.dataclass(frozen=True)
class LocalUserParticipant(AbstractParticipant):
    user: get_user_model()

    def new_participation(self, shift):
        return LocalParticipation(shift=shift, user=self.user)

    def participation_for(self, shift):
        try:
            return LocalParticipation.objects.get(shift=shift, user=self.user)
        except LocalParticipation.DoesNotExist:
            return None

    def all_participations(self):
        return LocalParticipation.objects.filter(user=self.user)

    def reverse_signup_action(self, shift):
        return reverse("core:signup_action", kwargs=dict(pk=shift.pk))

    def reverse_event_detail(self, event):
        return event.get_absolute_url()


@dataclasses.dataclass(frozen=True)
class PlaceholderParticipant(AbstractParticipant):
    def new_participation(self, shift):
        return PlaceholderParticipation(
            shift=shift, first_name=self.first_name, last_name=self.last_name
        )

    def participation_for(self, shift):
        try:
            return PlaceholderParticipation.objects.get(
                shift=shift, first_name=self.first_name, last_name=self.last_name
            )
        except PlaceholderParticipation.DoesNotExist:
            return None

    def all_participations(self):
        return AbstractParticipation.objects.none()

    def reverse_signup_action(self, shift):
        raise NotImplementedError

    def reverse_event_detail(self, event):
        raise NotImplementedError

    @property
    def icon(self):
        return mark_safe(
            f'<span class="fa fa-user-tag" data-toggle="tooltip" data-placement="left" title="{_("Placeholder")}"></span>'
        )
