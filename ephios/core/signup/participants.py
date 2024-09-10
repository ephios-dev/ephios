import dataclasses
from datetime import date
from typing import Collection, Optional

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from ephios.core.models import AbstractParticipation, LocalParticipation
from ephios.core.models.events import PlaceholderParticipation
from ephios.core.services.qualification import (
    QualificationUniverse,
    collect_all_included_qualifications,
)
from ephios.core.signals import participant_from_request


@dataclasses.dataclass(frozen=True)
class AbstractParticipant:
    display_name: str
    qualifications: Collection = dataclasses.field(hash=False, compare=False)
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
        return self.display_name

    def new_participation(self, shift):
        raise NotImplementedError

    def participation_for(self, shift):
        """Return the participation object for a shift. Return None if it does not exist."""
        raise NotImplementedError

    def all_participations(self):
        """Return all participations for this participant"""
        raise NotImplementedError

    def collect_all_qualifications(self) -> set:
        return collect_all_included_qualifications(self.qualifications)

    @cached_property
    def skill(self):
        graph = QualificationUniverse.get_graph()
        all_qualification_uuids = set(
            graph.spread_from([qualification.uuid for qualification in self.qualifications])
        )
        return all_qualification_uuids

    def has_qualifications(self, qualifications):
        return set(qualifications) <= set(self.collect_all_qualifications())

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
        return reverse("core:signup_action", kwargs={"pk": shift.pk})

    def reverse_event_detail(self, event):
        return event.get_absolute_url()


@dataclasses.dataclass(frozen=True)
class PlaceholderParticipant(AbstractParticipant):
    def new_participation(self, shift):
        return PlaceholderParticipation(shift=shift, display_name=self.display_name)

    def participation_for(self, shift):
        try:
            return PlaceholderParticipation.objects.get(shift=shift, display_name=self.display_name)
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
        title = _("Placeholder")
        return mark_safe(
            f'<span class="fa fa-user-tag" data-toggle="tooltip" data-placement="left" title="{title}"></span>'
        )


def get_nonlocal_participant_from_request(request):
    for _, participant in participant_from_request.send(sender=None, request=request):
        if participant is not None:
            return participant
    raise PermissionDenied
