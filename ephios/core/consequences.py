import operator
from datetime import date, datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import IntegerField, OuterRef, Q, Subquery
from django.db.models.fields.json import KeyTransform
from django.db.models.functions import Cast
from django.template.defaultfilters import floatformat
from django.utils.formats import date_format
from django.utils.timezone import make_aware
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
from ephios.core.signals import register_consequence_handlers


def installed_consequence_handlers():
    for _, handlers in register_consequence_handlers.send_to_all_plugins(None):
        yield from (h() for h in handlers)


def consequence_handler_from_slug(slug):
    for handler in installed_consequence_handlers():
        if handler.slug == slug:
            return handler
    raise ValueError(_("Consequence Handler '{slug}' was not found.").format(slug=slug))


def editable_consequences(user):
    handlers = list(installed_consequence_handlers())
    qs = Consequence.objects.all().select_related("user")
    for handler in handlers:
        qs = handler.filter_queryset(qs, user)
    return qs.filter(slug__in=map(operator.attrgetter("slug"), handlers)).distinct()


def pending_consequences(user):
    qs = Consequence.objects.filter(user=user, state=Consequence.States.NEEDS_CONFIRMATION)
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
    def filter_queryset(cls, qs, user: UserProfile):
        """
        Return a filtered that excludes consequences with the slug of this class that the user is not allowed to edit.
        Consequences should also be annotated with values needed for rendering.
        """
        raise NotImplementedError


class WorkingHoursConsequenceHandler(BaseConsequenceHandler):
    slug = "ephios.grant_working_hours"

    @classmethod
    def create(
        cls,
        user: UserProfile,
        when: date,
        hours: float,
        reason: str,
    ):
        return Consequence.objects.create(
            slug=cls.slug,
            user=user,
            data={"hours": hours, "date": when, "reason": reason},
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
        return _("{user} obtains {hours} working hours for {reason} on {date}").format(
            user=consequence.user.get_full_name(),
            hours=floatformat(consequence.data.get("hours"), arg=-2),
            reason=consequence.data.get("reason"),
            date=date_format(consequence.data.get("date")),
        )

    @classmethod
    def filter_queryset(cls, qs, user: UserProfile):
        return qs.filter(
            ~Q(slug=cls.slug)
            | Q(
                user__groups__in=get_objects_for_user(
                    user, "decide_workinghours_for_group", klass=Group
                )
            )
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
            data={
                "qualification_id": qualification.id,
                "event_id": None if shift is None else shift.event_id,
                "expires": expires,
            },
        )

    @classmethod
    def execute(cls, consequence):
        qg, created = QualificationGrant.objects.get_or_create(
            defaults={"expires": consequence.data["expires"]},
            user=consequence.user,
            qualification_id=consequence.data["qualification_id"],
        )
        if not created:
            qg.expires = max(
                qg.expires,
                consequence.data["expires"],
                key=lambda dt: dt or make_aware(datetime.max),
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
                id=Cast(consequence.data["qualification_id"], IntegerField())
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
    def filter_queryset(cls, qs, user: UserProfile):
        qs = qs.annotate(
            qualification_id=Cast(KeyTransform("qualification_id", "data"), IntegerField()),
            event_id=Cast(KeyTransform("event_id", "data"), IntegerField()),
        ).annotate(
            qualification_title=Subquery(
                Qualification.objects.filter(id=OuterRef("qualification_id")).values("title")[:1]
            ),
            event_title=Subquery(Event.objects.filter(id=OuterRef("event_id")).values("title")[:1]),
        )

        return qs.filter(
            ~Q(slug=cls.slug)
            # Qualifications can be granted by people who...
            | Q(  # are responsible for the event the consequence originated from, if applicable
                event_id__in=get_objects_for_user(user, perms="change_event", klass=Event),
            )
            | Q(  # can edit the affected user anyway
                user__in=get_objects_for_user(
                    user, perms="change_userprofile", klass=get_user_model()
                )
            )
        )
