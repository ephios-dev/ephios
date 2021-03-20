from urllib.parse import urljoin

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.formats import date_format
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _
from guardian.shortcuts import get_users_with_perms

from ephios.core.models import AbstractParticipation, Event, LocalParticipation, UserProfile
from ephios.core.models.users import Notification
from ephios.core.signals import register_notification_types
from ephios.core.signup import LocalUserParticipant


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

    @property
    def slug(self):
        return NotImplementedError

    @property
    def description(self):
        return NotImplementedError

    @classmethod
    def get_subject(cls, notification):
        raise NotImplementedError

    @classmethod
    def as_plaintext(cls, notification):
        raise NotImplementedError

    @classmethod
    def as_html(cls, notification):
        return render_to_string("email_base.html", {"message_text": cls.as_plaintext(notification)})


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
    def as_plaintext(cls, notification):
        return _(
            "You're receiving this email because your account at ephios has been updated.\n"
            "You can see the changes in your profile: {url}\n"
            "Your username is your email address: {email}\n"
        ).format(
            url=urljoin(settings.SITE_URL, reverse("core:profile")), email=notification.user.email
        )


class NewProfileNotification(AbstractNotificationHandler):
    slug = "ephios_new_profile"
    title = _("A new profile has been created")
    unsubscribe_allowed = False

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
    def as_plaintext(cls, notification):
        reset_link = reverse("password_reset_confirm", kwargs=notification.data)
        return _(
            "You're receiving this email because a new account has been created for you at ephios.\n"
            "Please go to the following page and choose a password: {url}\n"
            "Your username is your email address: {email}\n"
        ).format(url=urljoin(settings.SITE_URL, reset_link), email=notification.user.email)

    @classmethod
    def as_html(cls, notification):
        return render_to_string(
            "core/mails/new_account_email.html",
            {
                **{"site_url": settings.SITE_URL, "email": notification.user.email},
                **notification.data,
            },
        )


class NewEventNotification(AbstractNotificationHandler):
    slug = "ephios_new_event"
    title = _("A new event has been added")

    @classmethod
    def send(cls, event: Event, **kwargs):
        notifications = []
        for user in get_users_with_perms(event, only_with_perms_in=["view_event"]):
            notifications.append(
                Notification(slug=cls.slug, user=user, data=dict(event_id=event.id, **kwargs))
            )
        Notification.objects.bulk_create(notifications)

    @classmethod
    def get_subject(cls, notification):
        event = Event.objects.get(pk=notification.data.get("event_id"))
        return _("New {type}: {title}").format(type=event.type, title=event.title)

    @classmethod
    def as_plaintext(cls, notification):
        event = Event.objects.get(pk=notification.data.get("event_id"))
        return _(
            "A new {type} ({title}, {location}) has been added.\n"
            "Further information: {description}\n"
            "You can view the event here: {url}"
        ).format(
            type=event.type,
            title=event.title,
            location=event.location,
            description=event.description,
            url=urljoin(settings.SITE_URL, event.get_absolute_url()),
        )

    @classmethod
    def as_html(cls, notification):
        event = Event.objects.get(pk=notification.data.get("event_id"))
        return render_to_string(
            "core/mails/new_event.html", {"event": event, "site_url": settings.SITE_URL}
        )


class ParticipationConfirmedNotification(AbstractNotificationHandler):
    slug = "ephios_participation_confirmed"
    title = _("Your participation has been confirmed")

    @classmethod
    def send(cls, participation: AbstractParticipation):
        user = (
            participation.user
            if participation.get_real_instance_class() == LocalParticipation
            else None
        )
        Notification.objects.create(
            slug=cls.slug,
            user=user,
            data=dict(participation_id=participation.id, email=participation.participant.email),
        )

    @classmethod
    def get_subject(cls, notification):
        event = AbstractParticipation.objects.get(
            id=notification.data.get("participation_id")
        ).shift.event
        return _("Participation confirmed for {event}").format(event=event)

    @classmethod
    def as_plaintext(cls, notification):
        shift = AbstractParticipation.objects.get(
            id=notification.data.get("participation_id")
        ).shift
        return _("Your participation for {shift} is now confirmed.").format(shift=shift)


class ParticipationRejectedNotification(AbstractNotificationHandler):
    slug = "ephios_participation_rejected"
    title = _("Your participation has been rejected")

    @classmethod
    def send(cls, participation: AbstractParticipation):
        user = (
            participation.user
            if participation.get_real_instance_class() == LocalParticipation
            else None
        )
        Notification.objects.create(
            slug=cls.slug,
            user=user,
            data=dict(participation_id=participation.id, email=participation.participant.email),
        )

    @classmethod
    def get_subject(cls, notification):
        event = AbstractParticipation.objects.get(
            id=notification.data.get("participation_id")
        ).shift.event
        return _("Participation rejected for {event}").format(event=event)

    @classmethod
    def as_plaintext(cls, notification):
        shift = AbstractParticipation.objects.get(
            id=notification.data.get("participation_id")
        ).shift
        return _("Your participation for {shift} has been rejected by a responsible user.").format(
            shift=shift
        )


class ResponsibleParticipationRequested(AbstractNotificationHandler):
    slug = "ephios_participation_responsible_requested"
    title = _("A participation has been requested for your event")

    @classmethod
    def send(cls, participation: AbstractParticipation):
        responsible_users = get_users_with_perms(
            participation.shift.event, only_with_perms_in=["change_event"]
        ).distinct()
        disposition_url = urljoin(
            settings.SITE_URL,
            reverse("core:shift_disposition", kwargs=dict(pk=participation.shift.pk)),
        )
        notifications = []
        for user in responsible_users:
            notifications.append(
                Notification(
                    slug=cls.slug,
                    user=user,
                    data=dict(
                        participation_id=participation.id,
                        disposition_url=disposition_url,
                    ),
                )
            )
        Notification.objects.bulk_create(notifications)

    @classmethod
    def get_subject(cls, notification):
        participation = AbstractParticipation.objects.get(
            id=notification.data.get("participation_id")
        )
        participation_state = participation.get_state_display()
        return _("Participation {state} for {event}").format(
            state=participation_state, event=participation.shift.event
        )

    @classmethod
    def as_plaintext(cls, notification):
        participation = AbstractParticipation.objects.get(
            id=notification.data.get("participation_id")
        )
        if participation.shift.signup_method.uses_requested_state:
            return _(
                "{participant} has requested a participation for {shift}. You can decide about it at {disposition_url}"
            ).format(
                shift=participation.shift,
                participant=participation.participant,
                disposition_url=notification.data.get("disposition_url"),
            )
        return _("{participant} signed up for {shift}").format(
            participant=participation.participant, shift=participation.shift
        )


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
                Notification(slug=cls.slug, user=user, data=dict(event_id=event.id))
            )
        Notification.objects.bulk_create(notifications)

    @classmethod
    def get_subject(cls, notification):
        event = Event.objects.get(pk=notification.data.get("event_id"))
        return _("Help needed for {title}").format(title=event.title)

    @classmethod
    def as_plaintext(cls, notification):
        event = Event.objects.get(pk=notification.data.get("event_id"))
        return _(
            "Your support is needed for {title} ({start} - {end}). \nYou can view the event here: {url}"
        ).format(
            title=event.title,
            start=date_format(event.get_start_time(), "SHORT_DATETIME_FORMAT"),
            end=date_format(event.get_end_time(), "SHORT_DATETIME_FORMAT"),
            url=urljoin(settings.SITE_URL, event.get_absolute_url()),
        )


class CustomEventParticipantNotification(AbstractNotificationHandler):
    slug = "ephios_custom_event_participant"
    title = _("Message to all participants")
    unsubscribe_allowed = False

    @classmethod
    def send(cls, event: Event, content: str):
        participants = set()
        for shift in event.shifts.all():
            participants.update(shift.get_participants())
        notifications = []
        for participant in participants:
            user = participant.user if isinstance(participant, LocalUserParticipant) else None
            notifications.append(
                Notification(
                    slug=cls.slug,
                    user=user,
                    data=dict(email=participant.email, event_id=event.id, content=content),
                )
            )
        Notification.objects.bulk_create(notifications)

    @classmethod
    def get_subject(cls, notification):
        event = Event.objects.get(pk=notification.data.get("event_id"))
        return _("Information for your participation at {title}").format(title=event.title)

    @classmethod
    def as_plaintext(cls, notification):
        return notification.data.get("content")


CORE_NOTIFICATION_TYPES = [
    ProfileUpdateNotification,
    NewProfileNotification,
    ParticipationRejectedNotification,
    ParticipationConfirmedNotification,
    ResponsibleParticipationRequested,
    NewEventNotification,
    EventReminderNotification,
    CustomEventParticipantNotification,
]
