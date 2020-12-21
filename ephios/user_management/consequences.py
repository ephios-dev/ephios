import functools
import operator
from datetime import datetime
from decimal import Decimal

import django.dispatch
from django.db.models import Q
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _
from guardian.shortcuts import get_objects_for_user

from ephios.event_management.models import Event, Shift
from ephios.user_management.models import (
    Consequence,
    Qualification,
    QualificationGrant,
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
    return Consequence.objects.filter(
        functools.reduce(
            operator.or_,
            (handler.editable_by_filter(user) for handler in all_consequence_handlers()),
            Q(),
        )
    )


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
        The default implementation lists consequences caused by shifts that can be edited by the given user.
        """
        return Q(
            slug=cls.slug,
            shift__isnull=False,
            shift__event__in=get_objects_for_user(user, perms="change_event", klass=Event),
        )


class WorkingHoursConsequenceHandler(BaseConsequenceHandler):
    slug = "ephios.grant_working_hours"

    @classmethod
    def create(
        cls,
        user: UserProfile,
        when: datetime,
        hours: Decimal,
        reason: str,
    ):
        c = Consequence.objects.create(
            slug=cls.slug,
            user=user,
            data=dict(hours=hours, datetime=when.isoformat(), reason=reason),
        )
        return c

    @classmethod
    def execute(cls, consequence):
        WorkingHours.objects.create(
            user=consequence.user,
            datetime=datetime.fromisoformat(consequence.data["datetime"]),
            hours=consequence.data["hours"],
            reason=consequence.data.get("reason"),
        )

    @classmethod
    def render(cls, consequence):
        return _("{user} logs {hours} hours: {reason}").format(
            user=consequence.user.get_full_name(),
            hours=str(consequence.data.get("hours")),
            reason=consequence.data.get("reason"),
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
        c = Consequence.objects.create(
            slug=cls.slug,
            user=user,
            shift=shift,
            data=dict(
                qualification_id=qualification.id,
                expires=expires.isoformat() if expires is not None else None,
            ),
        )

        return c

    @classmethod
    def execute(cls, consequence):
        expires_str = consequence.data["expires"]
        expires = None if not expires_str else datetime.fromisoformat(expires_str)
        qg, created = QualificationGrant.objects.get_or_create(
            defaults=dict(
                expires=expires,
            ),
            user=consequence.user,
            qualification_id=consequence.data["qualification_id"],
        )
        if not created:
            qg.expires = max(qg.expires, expires, key=lambda dt: dt or datetime.max)
            qg.save()

    @classmethod
    def render(cls, consequence):
        s = _("{user} acquires '{qualification}' after participating in {shift}.").format(
            user=consequence.user.get_full_name(),
            qualification=str(Qualification.objects.get(pk=consequence.data["qualification_id"])),
            shift=str(consequence.shift),
        )
        if (expires_str := consequence.data["expires"]) is not None:
            s += " " + _("It will be valid until {date}.").format(
                date=date_format(datetime.fromisoformat(expires_str))
            )
        return s
