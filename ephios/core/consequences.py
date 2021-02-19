import functools
import operator
from datetime import datetime

import django.dispatch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import OuterRef, Q, Subquery
from django.db.models.fields.json import KeyTransform
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _
from guardian.shortcuts import get_objects_for_user

from ephios.core.models import (
    Consequence,
    Event,
    Qualification,
    QualificationGrant,
    Shift,
    UserProfile,
    WorkingHours,
)

register_consequence_handlers = django.dispatch.Signal()


def all_consequence_handlers():
    for _, handlers in register_consequence_handlers.send(None):
        yield from (h() for h in handlers)


def consequence_handler_from_slug(slug):
    for handler in all_consequence_handlers():
        if handler.slug == slug:
            return handler
    raise ValueError(_("Consequence Handler '{slug}' was not found.").format(slug=slug))


def editable_consequences(user):
    handlers = list(all_consequence_handlers())
    qs = Consequence.objects.filter(
        functools.reduce(
            operator.or_,
            (handler.editable_by_filter(user) for handler in handlers),
            Q(),
        )
    ).distinct()
    for handler in handlers:
        qs = handler.annotate_queryset(qs)
    return qs


class ConsequenceError(Exception):
    pass


class BaseConsequenceHandler:
    @property
    def slug(self):
        raise NotImplementedError

    @classmethod
    def execute(cls, consequence):
        """
        Gets a consequence and tries to execute whatever it is the consequence wants to happen.
        """
        raise NotImplementedError

    @classmethod
    def render(cls, consequence):
        """
        Return html describing the action to be done as a consequence of what.
        Return None if you cannot handle this consequence.
        """
        raise NotImplementedError

    @classmethod
    def editable_by_filter(cls, user: UserProfile):
        """
        Return a Q object to filter consequence objects of this type that can be confirmed by the given user.
        """
        raise NotImplementedError

    @classmethod
    def annotate_queryset(cls, qs):
        """
        Annotate a queryset of heterogeneous consequences to avoid needing additional queries for rendering a consequence.
        Does no annotations by default.
        """
        return qs


class WorkingHoursConsequenceHandler(BaseConsequenceHandler):
    slug = "ephios.grant_working_hours"

    @classmethod
    def create(
        cls,
        user: UserProfile,
        when: datetime,
        hours: float,
        reason: str,
    ):
        return Consequence.objects.create(
            slug=cls.slug,
            user=user,
            data=dict(hours=hours, date=when, reason=reason),
        )

    @classmethod
    def execute(cls, consequence):
        WorkingHours.objects.create(
            user=consequence.user,
            date=consequence.data["date"],
            hours=consequence.data["hours"],
            reason=consequence.data.get("reason"),
        )

    @classmethod
    def render(cls, consequence):
        return _("{user} logs {hours:.1f} hours on {date}. Reason: {reason}").format(
            user=consequence.user.get_full_name(),
            hours=consequence.data.get("hours"),
            reason=consequence.data.get("reason"),
            date=date_format(consequence.data.get("date")),
        )

    @classmethod
    def editable_by_filter(cls, user):
        return Q(
            slug=cls.slug,
            user__groups__in=get_objects_for_user(
                user, "decide_workinghours_for_group", klass=Group
            ),
        )


class QualificationConsequenceHandler(BaseConsequenceHandler):
    slug = "ephios.grant_qualification"

    @classmethod
    def create(
        cls,
        user: UserProfile,
        qualification: Qualification,
        expires: datetime = None,
        shift: Shift = None,
    ):
        return Consequence.objects.create(
            slug=cls.slug,
            user=user,
            data=dict(
                qualification_id=qualification.id,
                event_id=None if shift is None else shift.event_id,
                expires=expires,
            ),
        )

    @classmethod
    def execute(cls, consequence):
        qg, created = QualificationGrant.objects.get_or_create(
            defaults=dict(
                expires=consequence.data["expires"],
            ),
            user=consequence.user,
            qualification_id=consequence.data["qualification_id"],
        )
        if not created:
            qg.expires = max(
                qg.expires, consequence.data["expires"], key=lambda dt: dt or datetime.max
            )
            qg.save()

    @classmethod
    def render(cls, consequence):
        # Get all the strings we need from the annotations, or fetch them from DB as backup
        try:  # try the annotation
            event_title = consequence.event_title
        except AttributeError:
            if event_id := consequence.data["event_id"]:  # fetch from DB as backup
                event_title = Event.objects.get(id=event_id).title
            else:  # no event has been associated
                event_title = None

        try:
            qualification_title = consequence.qualification_title
        except AttributeError:
            qualification_title = Qualification.objects.get(
                id=consequence.data["qualification_id"]
            ).title

        if expires := consequence.data.get("expires"):
            expires = date_format(expires)

        user = consequence.user.get_full_name()

        # build string based on available data

        if event_title:
            s = _("{user} acquires '{qualification}' after participating in {event}.").format(
                user=user, qualification=qualification_title, event=event_title
            )
        else:
            s = _("{user} acquires '{qualification}'.").format(
                user=user,
                qualification=qualification_title,
            )

        if expires:
            s += " " + _("(valid until {expires_str})").format(expires_str=expires)
        return s

    @classmethod
    def editable_by_filter(cls, user: UserProfile):
        # Qualifications can be granted by people who...
        return Q(slug=cls.slug,) & (
            Q(  # are responsible for the event the consequence originated from, if applicable
                data__event_id__isnull=False,
                data__event_id__in=get_objects_for_user(user, perms="change_event", klass=Event),
            )
            | Q(  # can edit the affected user anyway
                user__in=get_objects_for_user(
                    user, perms="core.change_userprofile", klass=get_user_model()
                )
            )
        )

    @classmethod
    def annotate_queryset(cls, qs):
        return qs.annotate(
            qualification_id=KeyTransform("qualification_id", "data"),
            event_id=KeyTransform("event_id", "data"),
        ).annotate(
            qualification_title=Subquery(
                Qualification.objects.filter(id=OuterRef("qualification_id")).values("title")[:1]
            ),
            event_title=Subquery(Event.objects.filter(id=OuterRef("event_id")).values("title")[:1]),
        )
