from urllib.parse import urljoin

from django.conf import settings
from django.core import mail
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.formats import date_format
from django.utils.translation import gettext as _
from guardian.shortcuts import get_users_with_perms

from ephios.core.models import AbstractParticipation, LocalParticipation, UserProfile
from ephios.extra.permissions import get_groups_with_perms


def new_event(event):
    messages = []
    users = UserProfile.objects.filter(
        groups__in=get_groups_with_perms(event, only_with_perms_in=["view_event"]), is_active=True
    ).distinct()
    responsible_users = get_users_with_perms(event, only_with_perms_in=["change_event"]).distinct()
    responsible_persons_mails = list(responsible_users.values_list("email", flat=True))

    subject = _("New {type}: {title}").format(type=event.type, title=event.title)
    text_content = _(
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
    html_content = render_to_string(
        "core/mails/new_event.html", {"event": event, "site_url": settings.SITE_URL}
    )

    for user in users:
        if user.preferences["notifications__new_event"]:
            message = EmailMultiAlternatives(
                to=[user.email],
                subject=subject,
                body=text_content,
                reply_to=responsible_persons_mails,
            )
            message.attach_alternative(html_content, "text/html")
            messages.append(message)
    mail.get_connection().send_messages(messages)


def participation_state_changed(participation: AbstractParticipation):
    messages = []

    # send mail to the participant whose participation has been changed
    mail_requested = participation.participant.email is not None
    if participation.get_real_instance_class() == LocalParticipation:
        if participation.state == AbstractParticipation.States.CONFIRMED:
            mail_requested = participation.user.preferences["notifications__confirm_participation"]
        if participation.state == AbstractParticipation.States.RESPONSIBLE_REJECTED:
            mail_requested = participation.user.preferences["notifications__reject_participation"]

    if mail_requested and participation.state in (
        AbstractParticipation.States.CONFIRMED,
        AbstractParticipation.States.RESPONSIBLE_REJECTED,
    ):
        text_content = _(
            "The status for your participation for {shift} has changed. It is now {status}."
        ).format(shift=participation.shift, status=participation.get_state_display())
        html_content = render_to_string("email_base.html", {"message_text": text_content})
        message = EmailMultiAlternatives(
            to=[participation.participant.email],
            subject=_("Your participation state changed"),
            body=text_content,
        )
        message.attach_alternative(html_content, "text/html")
        messages.append(message)

    # send mail to responsible users
    if participation.state == AbstractParticipation.States.REQUESTED or (
        not participation.shift.signup_method.uses_requested_state
        and AbstractParticipation.States.CONFIRMED
    ):
        responsible_users = get_users_with_perms(
            participation.shift.event, only_with_perms_in=["change_event"]
        ).distinct()
        subject = _("Participation was changed for your event")
        text_content = _(
            "The participation of {participant} for {shift} was changed. The status is now {status}"
        ).format(
            participant=participation.participant,
            shift=participation.shift,
            status=participation.get_state_display(),
        )
        html_content = render_to_string("email_base.html", {"message_text": text_content})
        for user in responsible_users:
            if participation.shift.event.type in user.preferences.get(
                "responsible_notifications__requested_participation"
            ):
                message = EmailMultiAlternatives(
                    to=[user.email], subject=subject, body=text_content
                )
                message.attach_alternative(html_content, "text/html")
                messages.append(message)

    mail.get_connection().send_messages(messages)


def remind_users_not_participating(event):
    users_not_participating = UserProfile.objects.exclude(
        pk__in=AbstractParticipation.objects.filter(shift__event=event).values_list(
            "localparticipation__user", flat=True
        )
    )
    responsible_users = get_users_with_perms(event, only_with_perms_in=["change_event"]).distinct()
    responsible_persons_mails = list(responsible_users.values_list("email", flat=True))

    subject = _("Help needed for {title}").format(title=event.title)
    text_content = _(
        "Your support is needed for {title} ({start} - {end}). \nYou can view the event here: {url}"
    ).format(
        title=event.title,
        start=date_format(event.get_start_time(), "SHORT_DATETIME_FORMAT"),
        end=date_format(event.get_end_time(), "SHORT_DATETIME_FORMAT"),
        url=urljoin(settings.SITE_URL, event.get_absolute_url()),
    )
    html_content = render_to_string("email_base.html", {"message_text": text_content})
    messages = []

    for user in users_not_participating:
        message = EmailMultiAlternatives(
            to=[user.email],
            subject=subject,
            body=text_content,
            reply_to=responsible_persons_mails,
        )
        message.attach_alternative(html_content, "text/html")
        messages.append(message)
    mail.get_connection().send_messages(messages)


def mail_to_participants(event, content, sender):
    participants = set()
    for shift in event.shifts.all():
        participants.update(shift.get_participants())

    subject = _("Information for your participation at {title}").format(title=event.title)
    html_content = render_to_string("email_base.html", {"message_text": content})
    messages = []

    for participant in participants:
        message = EmailMultiAlternatives(
            to=[participant.email],
            subject=subject,
            body=content,
            reply_to=[sender.email],
        )
        message.attach_alternative(html_content, "text/html")
        messages.append(message)
    mail.get_connection().send_messages(messages)
