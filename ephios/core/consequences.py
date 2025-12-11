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
    LocalConsequence,
    Event,
    Qualification,
    QualificationGrant,
    Shift,
    UserProfile,
    WorkingHours,
)
from ephios.core.models.users import AbstractConsequence
from ephios.core.signals import register_consequence_handlers
from ephios.core.signup.participants import AbstractParticipant


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
    consequence_classes = AbstractConsequence.__subclasses__()

    qs = AbstractConsequence.objects.filter(slug__in=map(operator.attrgetter("slug"), handlers)).distinct()
    q_obj = Q()
    for handler in handlers:
        for ConcreteConsequence in consequence_classes:
            q_obj = q_obj | ConcreteConsequence.filter_editable_by_user(handler, user)
    return qs.filter(q_obj)


def pending_consequences(user):
    qs = LocalConsequence.objects.filter(user=user, state=LocalConsequence.States.NEEDS_CONFIRMATION)
    return qs


class ConsequenceError(Exception):
    pass


class UnsupportedConsequenceTarget(ConsequenceError):
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
    def filter_editable_by_user(cls, user: UserProfile) -> Q:
        """
        Return a Q object that include consequences with the slug of this class that the user is allowed to edit.
        """
        raise NotImplementedError


class WorkingHoursConsequenceHandler(BaseConsequenceHandler):
    slug = "ephios.grant_working_hours"

    @classmethod
    def create(
        cls,
        participant: AbstractParticipant,
        when: date,
        hours: float,
        reason: str,
    ):
        consequence = participant.new_consequence()
        consequence.slug = cls.slug
        consequence.data = {"hours": hours, "date": when, "reason": reason}
        consequence.save()
        return consequence

    @classmethod
    def execute(cls, consequence):
        if not isinstance(consequence, LocalConsequence):
            raise UnsupportedConsequenceTarget
        WorkingHours.objects.create(
            user=consequence.user,
            date=consequence.data["date"],
            hours=consequence.data["hours"],
            reason=consequence.data.get("reason"),
        )

    @classmethod
    def render(cls, consequence):
        return _("obtains {hours} working hours for {reason} on {date}").format(
            hours=floatformat(consequence.data.get("hours"), arg=-2),
            reason=consequence.data.get("reason"),
            date=date_format(consequence.data.get("date")),
        )

    @classmethod
    def filter_editable_by_user(cls, user: UserProfile):
        return Q(slug=cls.slug,
                localconsequence__user__groups__in=get_objects_for_user(
                    user, "decide_workinghours_for_group", klass=Group
                )
            )


class QualificationConsequenceHandler(BaseConsequenceHandler):
    slug = "ephios.grant_qualification"

    @classmethod
    def create(
        cls,
        participant: AbstractParticipant,
        qualification: Qualification,
        expires: datetime = None,
        shift: Shift = None,
    ):
        consequence = participant.new_consequence()
        consequence.slug = cls.slug
        consequence.data = {
                "qualification_id": qualification.id,
                "event_id": None if shift is None else shift.event_id,
                "expires": expires,
            }
        consequence.save()
        return consequence

    @classmethod
    def execute(cls, consequence):
        if not isinstance(consequence, LocalConsequence):
            raise UnsupportedConsequenceTarget
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
        try:
            try:  # try the annotation
                event_title = consequence.event_title
            except AttributeError:
                if event_id := consequence.data["event_id"]:  # fetch from DB as backup
                    event_title = Event.objects.get(id=event_id).title
                else:  # no event has been associated
                    event_title = None
        except Event.DoesNotExist:
            event_title = _("deleted event")

        try:
            qualification_title = consequence.qualification_title
        except AttributeError:
            qualification_title = Qualification.objects.get(
                id=Cast(consequence.data["qualification_id"], IntegerField())
            ).title

        if expires := consequence.data.get("expires"):
            expires = date_format(expires)

        # build string based on available data

        if event_title:
            s = _("acquires '{qualification}' after participating in {event}.").format(
                qualification=qualification_title, event=event_title
            )
        else:
            s = _("acquires '{qualification}'.").format(
                qualification=qualification_title,
            )

        if expires:
            s += " " + _("(valid until {expires_str})").format(expires_str=expires)
        return s

    @classmethod
    def filter_editable_by_user(cls, user: UserProfile):
        return Q(slug=cls.slug) & Q(
            # Qualifications can be granted by people who...
            Q(  # are responsible for the event the consequence originated from, if applicable
                data__event_id__in=get_objects_for_user(user, perms="change_event", klass=Event),
            )
            | Q(  # can edit the affected user anyway
                localconsequence__user__in=get_objects_for_user(
                    user, perms="change_userprofile", klass=get_user_model()
                )
            )
        )
