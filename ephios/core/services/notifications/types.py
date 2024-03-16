from typing import List
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.formats import date_format
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _
from guardian.shortcuts import get_users_with_perms
from requests import PreparedRequest

from ephios.core.models import AbstractParticipation, Event, LocalParticipation, UserProfile
from ephios.core.models.users import Consequence, Notification
from ephios.core.signals import register_notification_types
from ephios.core.signup.participants import LocalUserParticipant
from ephios.core.templatetags.settings_extras import make_absolute

NOTIFICATION_READ_PARAM_NAME = "fromNotification"


def installed_notification_types():
    for _, handlers in register_notification_types.send_to_all_plugins(None):
        yield from (h for h in handlers)


def enabled_notification_types():
    for _, handlers in register_notification_types.send(None):
        yield from (h for h in handlers)


def notification_type_from_slug(slug):
    for notification in installed_notification_types():
        if notification.slug == slug:
            return notification
    raise ValueError(_("Notification type '{slug}' was not found.").format(slug=slug))


class AbstractNotificationHandler:
    unsubscribe_allowed = True
    email_template_name = "core/mails/notification.html"
    plaintext_template_name = "core/mails/notification.txt"

    @property
    def slug(self):
        return NotImplementedError

    @property
    def title(self):
        return NotImplementedError

    @classmethod
    def get_subject(cls, notification):
        raise NotImplementedError

    @classmethod
    def get_body(cls, notification):
        raise NotImplementedError

    @classmethod
    def is_obsolete(cls, notification):
        return False

    @classmethod
    def as_plaintext(cls, notification):
        return render_to_string(cls.plaintext_template_name, cls.get_render_context(notification))

    @classmethod
    def as_html(cls, notification):
        return render_to_string(cls.email_template_name, cls.get_render_context(notification))

    @classmethod
    def get_render_context(cls, notification):
        return {
            "subject": cls.get_subject(notification),
            "body": cls.get_body(notification),
            "notification": notification,
            "notification_settings_url": make_absolute(reverse("core:settings_notifications")),
        }

    @classmethod
    def get_actions(cls, notification):
        """
        Return a list of (label, url) tuples that make this notification actionable.
        The first url will be used as the primary action in push notifications.
        """
        return []

    @classmethod
    def get_actions_with_referrer(cls, notification):
        """
        Annotate the actions returned by any subclass with a reference to the originating notification.
        This is used by EphiosNotificationMiddleware to mark the corresponding notification as read
        once the user clicks on the link.
        """
        actions = []
        for label, url in cls.get_actions(notification):
            if urlparse(url).netloc in settings.GET_SITE_URL():
                req = PreparedRequest()
                req.prepare_url(url, {NOTIFICATION_READ_PARAM_NAME: notification.pk})
                url = req.url
            actions.append((label, url))
        return actions


class ProfileUpdateNotification(AbstractNotificationHandler):
    slug = "ephios_profile_update"
    title = _("Your profile has been edited")

    @classmethod
    def send(cls, user: UserProfile, **kwargs):
        return Notification.objects.create(slug=cls.slug, user=user, data=kwargs)

    @classmethod
    def get_subject(cls, notification):
        return _("ephios account updated")

    @classmethod
    def get_body(cls, notification):
        return _(
            "You're receiving this email because your account at ephios has been updated."
        ).format(url=cls._get_personal_data_url(notification), email=notification.user.email)

    @classmethod
    def get_actions(cls, notification):
        return [(str(_("View profile")), cls._get_personal_data_url(notification))]

    @classmethod
    def _get_personal_data_url(cls, notification):
        return make_absolute(reverse("core:settings_personal_data"))


class NewProfileNotification(AbstractNotificationHandler):
    slug = "ephios_new_profile"
    title = _("A new profile has been created")
    unsubscribe_allowed = False
    email_template_name = "core/mails/new_account_email.html"

    @classmethod
    def send(cls, user: UserProfile, **kwargs):
        uid = urlsafe_base64_encode(force_bytes(user.id))
        token = default_token_generator.make_token(user)
        return Notification.objects.create(
            slug=cls.slug, user=user, data={**{"uidb64": uid, "token": token}, **kwargs}
        )

    @classmethod
    def get_subject(cls, notification):
        return _("Welcome to ephios!")

    @classmethod
    def get_body(cls, notification):
        return _(
            "You're receiving this email because a new account has been created for you at ephios.\n"
            "Please go to the following page and choose a password: {url} \n"
            "Your username is your email address: {email}"
        ).format(url=cls._get_reset_url(notification), email=notification.user.email)

    @classmethod
    def get_actions(cls, notification):
        return [(str(_("Set password")), cls._get_reset_url(notification))]

    @classmethod
    def _get_reset_url(cls, notification):
        reset_link = reverse(
            "password_reset_confirm",
            kwargs={
                "uidb64": notification.data["uidb64"],
                "token": notification.data["token"],
            },
        )
        return make_absolute(reset_link)


class NewEventNotification(AbstractNotificationHandler):
    slug = "ephios_new_event"
    title = _("A new event has been added")
    email_template_name = "core/mails/new_event.html"

    @classmethod
    def send(cls, event: Event, **kwargs):
        notifications = []
        for user in get_users_with_perms(event, only_with_perms_in=["view_event"]):
            notifications.append(
                Notification(slug=cls.slug, user=user, data={"event_id": event.id, **kwargs})
            )
        Notification.objects.bulk_create(notifications)

    @classmethod
    def get_subject(cls, notification):
        event = Event.objects.get(pk=notification.data.get("event_id"))
        return _("New {type}: {title}").format(type=event.type, title=event.title)

    @classmethod
    def get_body(cls, notification):
        event = Event.objects.get(pk=notification.data.get("event_id"))
        return _(
            "A new {type} ({title}, {location}) has been added.\n"
            "Further information: {description}"
        ).format(
            type=event.type,
            title=event.title,
            location=event.location,
            description=event.description,
        )

    @classmethod
    def get_render_context(cls, notification):
        context = super().get_render_context(notification)
        event = Event.objects.get(pk=notification.data.get("event_id"))
        context["event"] = event
        return context

    @classmethod
    def get_actions(cls, notification):
        event = Event.objects.get(pk=notification.data.get("event_id"))
        return [(str(_("View event")), make_absolute(event.get_absolute_url()))]


class ParticipationMixin:
    @classmethod
    def is_obsolete(cls, notification):
        participation: AbstractParticipation = AbstractParticipation.objects.get(
            id=notification.data.get("participation_id")
        )
        return participation.state != notification.data["participation_state"]

    @classmethod
    def get_actions(cls, notification):
        participation = AbstractParticipation.objects.get(
            id=notification.data.get("participation_id")
        )
        return [
            (
                str(_("View event")),
                make_absolute(
                    participation.participant.reverse_event_detail(participation.shift.event)
                ),
            )
        ]

    @classmethod
    def send(cls, participation: AbstractParticipation, **additional_data):
        user = (
            participation.user
            if participation.get_real_instance_class() == LocalParticipation
            else None
        )
        Notification.objects.create(
            slug=cls.slug,
            user=user,
            data={
                "participation_id": participation.id,
                "participation_state": participation.state,
                "email": participation.participant.email,
                **additional_data,
            },
        )


class ParticipationStateChangeNotification(ParticipationMixin, AbstractNotificationHandler):
    slug = "ephios_participation_state_changed"
    title = _("The state of your participation has changed")

    @classmethod
    def get_subject(cls, notification):
        event = AbstractParticipation.objects.get(
            id=notification.data.get("participation_id")
        ).shift.event
        return _("Participation {state} for {event}").format(
            state=AbstractParticipation.States.labels_dict()[
                notification.data["participation_state"]
            ],
            event=event,
        )

    @classmethod
    def get_body(cls, notification):
        participation: AbstractParticipation = AbstractParticipation.objects.get(
            id=notification.data.get("participation_id")
        )
        shift = participation.shift
        message = ""
        match notification.data["participation_state"]:
            case AbstractParticipation.States.REQUESTED:
                message = _("You requested a participation for {shift}.").format(shift=shift)
            case AbstractParticipation.States.CONFIRMED:
                message = _("Your participation for {shift} is now confirmed.").format(shift=shift)
            case AbstractParticipation.States.RESPONSIBLE_REJECTED:
                return _(
                    "Your participation for {shift} has been rejected by a responsible user."
                ).format(shift=shift)
        if participation.has_customized_signup():
            message += f'\n\n{_("Your time is")} {participation.get_time_display()}'
        return message


class ParticipationCustomizationNotification(ParticipationMixin, AbstractNotificationHandler):
    slug = "ephios_participation_customized"
    title = _("A confirmed participation of yours has been tweaked by a responsible")

    # pylint: disable=arguments-differ
    @classmethod
    def send(cls, participation: AbstractParticipation, claims: List[str] = None):
        super().send(participation, claims=claims)

    @classmethod
    def get_subject(cls, notification):
        shift = AbstractParticipation.objects.get(
            id=notification.data.get("participation_id")
        ).shift
        return _("Participation tweaked for {shift}").format(shift=shift)

    @classmethod
    def get_body(cls, notification):
        shift = AbstractParticipation.objects.get(
            id=notification.data.get("participation_id")
        ).shift
        message = _(
            "Your participation for {shift} has been tweaked by a responsible user."
        ).format(shift=shift)
        message += "\n\n" + "\n".join(f"- {claim}" for claim in notification.data.get("claims", []))
        return message


class ResponsibleMixin:
    @classmethod
    def _responsible_users(cls, participation: AbstractParticipation):
        users = get_users_with_perms(
            participation.shift.event, only_with_perms_in=["change_event"]
        ).distinct()
        for user in users:
            if (
                participation.get_real_instance_class() != LocalParticipation
                or user != participation.user
            ):
                yield user

    @classmethod
    def send(cls, participation: AbstractParticipation, **additional_data):
        Notification.objects.bulk_create(
            [
                Notification(
                    slug=cls.slug,
                    user=user,
                    data={
                        "disposition_url": make_absolute(
                            reverse(
                                "core:shift_disposition", kwargs={"pk": participation.shift.pk}
                            ),
                        ),
                        "participation_id": participation.id,
                        "participation_state": participation.state,
                        **additional_data,
                    },
                )
                for user in cls._responsible_users(participation)
            ]
        )

    @classmethod
    def get_actions(cls, notification):
        participation = AbstractParticipation.objects.get(
            id=notification.data.get("participation_id")
        )
        return [
            (
                str(_("View event")),
                make_absolute(participation.shift.get_absolute_url()),
            ),
            (str(_("Disposition")), notification.data.get("disposition_url")),
        ]

    @classmethod
    def get_subject(cls, notification):
        event = AbstractParticipation.objects.get(
            id=notification.data.get("participation_id")
        ).shift.event
        return _("Participation {state} for {event}").format(
            state=AbstractParticipation.States.labels_dict()[
                notification.data["participation_state"]
            ],
            event=event,
        )


class ResponsibleParticipationAwaitsDispositionNotification(
    ResponsibleMixin, AbstractNotificationHandler
):
    slug = "ephios_participation_awaits_disposition"
    title = _("A participation for your event awaits disposition")

    @classmethod
    def is_obsolete(cls, notification):
        participation: AbstractParticipation = AbstractParticipation.objects.get(
            id=notification.data.get("participation_id")
        )
        return participation.state != AbstractParticipation.States.REQUESTED

    @classmethod
    def get_body(cls, notification):
        participation = AbstractParticipation.objects.get(
            id=notification.data.get("participation_id")
        )
        return _("{participant} has requested a participation for {shift}.").format(
            shift=participation.shift,
            participant=participation.participant,
        )


class ResponsibleParticipationStateChangeNotification(
    ResponsibleMixin, AbstractNotificationHandler
):
    slug = "ephios_participation_responsible_state_changed"
    title = _("A participation for your event has changed state")

    @classmethod
    def is_obsolete(cls, notification):
        participation: AbstractParticipation = AbstractParticipation.objects.get(
            id=notification.data.get("participation_id")
        )
        return participation.state != notification.data["participation_state"]

    @classmethod
    def get_body(cls, notification):
        participation = AbstractParticipation.objects.get(
            id=notification.data.get("participation_id")
        )
        return _("The participation of {participant} for {shift} is now {state}.").format(
            shift=participation.shift,
            participant=participation.participant,
            state=AbstractParticipation.States.labels_dict()[
                notification.data["participation_state"]
            ],
        )


class ResponsibleConfirmedParticipationDeclinedNotification(
    ResponsibleMixin, AbstractNotificationHandler
):
    slug = "ephios_participation_responsible_confirmed_declined"
    title = _("A participant declined after having been confirmed for your event")

    @classmethod
    def get_body(cls, notification):
        participation = AbstractParticipation.objects.get(
            id=notification.data.get("participation_id")
        )
        return _("{participant} declined their participation in {shift}.").format(
            participant=participation.participant, shift=participation.shift
        )


class ResponsibleConfirmedParticipationCustomizedNotification(
    ResponsibleMixin, AbstractNotificationHandler
):
    slug = "ephios_participation_responsible_confirmed_customized"
    title = _("A confirmed participant altered their participation")

    @classmethod
    def get_subject(cls, notification):
        participation = AbstractParticipation.objects.get(
            id=notification.data.get("participation_id")
        )
        return _("Participation altered for {event}").format(event=participation.shift.event)

    # pylint: disable=arguments-differ
    @classmethod
    def send(cls, participation: AbstractParticipation, claims: List[str] = None):
        super().send(participation, claims=claims or [])

    @classmethod
    def get_body(cls, notification):
        participation = AbstractParticipation.objects.get(
            id=notification.data.get("participation_id")
        )
        message = _("{participant} altered their participation in {shift}.").format(
            participant=participation.participant, shift=participation.shift
        )
        message += "\n\n" + "\n".join(f"- {claim}" for claim in notification.data.get("claims", []))
        return message


class EventReminderNotification(AbstractNotificationHandler):
    slug = "ephios_event_reminder"
    title = _("An event has vacant spots")
    unsubscribe_allowed = False

    @classmethod
    def send(cls, event: Event):
        users_not_participating = UserProfile.objects.exclude(
            pk__in=AbstractParticipation.objects.filter(shift__event=event).values_list(
                "localparticipation__user", flat=True
            )
        ).filter(pk__in=get_users_with_perms(event, only_with_perms_in=["view_event"]))
        notifications = []
        for user in users_not_participating:
            notifications.append(
                Notification(slug=cls.slug, user=user, data={"event_id": event.id})
            )
        Notification.objects.bulk_create(notifications)

    @classmethod
    def get_subject(cls, notification):
        event = Event.objects.get(pk=notification.data.get("event_id"))
        return _("Help needed for {title}").format(title=event.title)

    @classmethod
    def get_body(cls, notification):
        event = Event.objects.get(pk=notification.data.get("event_id"))
        return _("Your support is needed for {title} ({start} - {end}).").format(
            title=event.title,
            start=date_format(event.get_start_time(), "SHORT_DATETIME_FORMAT"),
            end=date_format(event.get_end_time(), "SHORT_DATETIME_FORMAT"),
        )

    @classmethod
    def get_actions(cls, notification):
        event = Event.objects.get(pk=notification.data.get("event_id"))
        return [(str(_("View event")), make_absolute(event.get_absolute_url()))]


class CustomEventParticipantNotification(AbstractNotificationHandler):
    slug = "ephios_custom_event_participant"
    title = _("Message to all participants")
    unsubscribe_allowed = False

    @classmethod
    def send(cls, event: Event, content: str):
        participants = set()
        notifications = []
        responsible_users = get_users_with_perms(
            event, with_superusers=False, only_with_perms_in=["change_event"]
        )
        for participation in AbstractParticipation.objects.filter(
            shift__event=event, state=AbstractParticipation.States.CONFIRMED
        ):
            participant = participation.participant
            if participant not in participants:
                participants.add(participant)
                user = participant.user if isinstance(participant, LocalUserParticipant) else None
                if user in responsible_users:
                    continue
                notifications.append(
                    Notification(
                        slug=cls.slug,
                        user=user,
                        data={
                            "email": participant.email,
                            "participation_id": participation.id,
                            "event_id": event.id,
                            "content": content,
                        },
                    )
                )
        for responsible in responsible_users:
            notifications.append(
                Notification(
                    slug=cls.slug,
                    user=responsible,
                    data={
                        "email": responsible.email,
                        "event_id": event.id,
                        "content": content,
                    },
                )
            )
        Notification.objects.bulk_create(notifications)

    @classmethod
    def get_subject(cls, notification):
        event = Event.objects.get(pk=notification.data.get("event_id"))
        return _("Information regarding {title}").format(title=event.title)

    @classmethod
    def get_body(cls, notification):
        return notification.data.get("content")

    @classmethod
    def get_actions(cls, notification):
        event = Event.objects.get(pk=notification.data.get("event_id"))
        participation = AbstractParticipation.objects.filter(
            pk=notification.data.get("participation_id")
        ).first()  # there is no participation for responsible users
        return [
            (
                str(_("View message")),
                make_absolute(reverse("core:notification_detail", kwargs={"pk": notification.pk})),
            ),
            (
                str(_("View event")),
                make_absolute(
                    participation.participant.reverse_event_detail(event)
                    if participation
                    else event.get_absolute_url()
                ),
            ),
        ]


class ConsequenceApprovedNotification(AbstractNotificationHandler):
    slug = "ephios_consequence_approved"
    title = _("Your request has been approved")

    @classmethod
    def send(cls, consequence: Consequence):
        Notification.objects.create(
            slug=cls.slug, user=consequence.user, data={"consequence_id": consequence.id}
        )

    @classmethod
    def get_subject(cls, notification):
        return _("Your request has been approved")

    @classmethod
    def get_body(cls, notification):
        consequence = Consequence.objects.get(id=notification.data.get("consequence_id"))
        return _('"{consequence}" has been approved.').format(consequence=consequence)


class ConsequenceDeniedNotification(AbstractNotificationHandler):
    slug = "ephios_consequence_denied"
    title = _("Your request has been denied")

    @classmethod
    def send(cls, consequence: Consequence):
        Notification.objects.create(
            slug=cls.slug, user=consequence.user, data={"consequence_id": consequence.id}
        )

    @classmethod
    def get_subject(cls, notification):
        return _("Your request has been denied")

    @classmethod
    def get_body(cls, notification):
        consequence = Consequence.objects.get(id=notification.data.get("consequence_id"))
        return _('"{consequence}" has been denied.').format(consequence=consequence)


CORE_NOTIFICATION_TYPES = [
    ProfileUpdateNotification,
    NewProfileNotification,
    ParticipationStateChangeNotification,
    ParticipationCustomizationNotification,
    ResponsibleParticipationAwaitsDispositionNotification,
    ResponsibleParticipationStateChangeNotification,
    ResponsibleConfirmedParticipationDeclinedNotification,
    ResponsibleConfirmedParticipationCustomizedNotification,
    NewEventNotification,
    EventReminderNotification,
    CustomEventParticipantNotification,
    ConsequenceApprovedNotification,
    ConsequenceDeniedNotification,
]
