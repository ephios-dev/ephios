from django.core import mail
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from guardian.shortcuts import get_users_with_perms

from ephios.event_management.models import AbstractParticipation, LocalParticipation
from ephios.extra.permissions import get_groups_with_perms
from ephios.settings import SITE_URL
from ephios.user_management.models import UserProfile


def new_event(event):
    messages = []
    users = UserProfile.objects.filter(
        groups__in=get_groups_with_perms(event, only_with_perms_in=["view_event"]), is_active=True
    ).distinct()
    responsible_users = get_users_with_perms(event, only_with_perms_in=["change_event"]).distinct()
    responsible_persons_mails = list(responsible_users.values_list("email", flat=True))

    subject = _("New {type}: {title}").format(type=event.type, title=event.title)
    text_content = _(
        "A new {type} ({title}) has been added. \n You can view it here: {link}"
    ).format(type=event.type, title=event.title, link=event.get_absolute_url())
    html_content = render_to_string(
        "event_management/mails/new_event.html", {"event": event, "site_url": SITE_URL}
    )

    for user in users:
        message = EmailMultiAlternatives(
            to=[user.email], subject=subject, body=text_content, reply_to=responsible_persons_mails
        )
        message.attach_alternative(html_content, "text/html")
        messages.append(message)
    mail.get_connection().send_messages(messages)


def participation_state_changed(participation: AbstractParticipation):
    if participation.state != AbstractParticipation.States.USER_DECLINED:
        messages = []

        # send mail to the participant whose participation has been changed
        if participation.participant.email is not None:
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
            message = EmailMultiAlternatives(to=[user.email], subject=subject, body=text_content)
            message.attach_alternative(html_content, "text/html")
            messages.append(message)

        mail.get_connection().send_messages(messages)
