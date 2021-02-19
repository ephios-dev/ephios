from urllib.parse import urljoin

from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext as _
from guardian.shortcuts import get_users_with_perms

from ephios.core.models import AbstractParticipation, LocalParticipation, UserProfile
from ephios.extra.permissions import get_groups_with_perms
from ephios.settings import SITE_URL


def send_account_creation_info_to_user(userprofile):
    subject = _("Welcome to ephios!")
    uid = urlsafe_base64_encode(force_bytes(userprofile.id))
    token = default_token_generator.make_token(userprofile)
    reset_link = reverse("password_reset_confirm", kwargs={"uidb64": uid, "token": token})
    text_content = _(
        "You're receiving this email because a new account has been created for you at ephios.\n"
        "Please go to the following page and choose a password: {url}\n"
        "Your username is your email address: {email}\n"
    ).format(url=urljoin(SITE_URL, reset_link), email=userprofile.email)

    html_content = render_to_string(
        "core/new_account_email.html",
        {"uid": uid, "token": token, "site_url": SITE_URL, "email": userprofile.email},
    )
    message = EmailMultiAlternatives(to=[userprofile.email], subject=subject, body=text_content)
    message.attach_alternative(html_content, "text/html")
    message.send()


def send_account_update_info_to_user(userprofile):
    subject = _("ephios account updated")
    url = reverse("core:profile")
    text_content = _(
        "You're receiving this email because your account at ephios has been updated.\n"
        "You can see the changes in your profile: {url}\n"
        "Your username is your email address: {email}\n"
    ).format(url=urljoin(SITE_URL, url), email=userprofile.email)

    html_content = render_to_string(
        "core/account_updated_email.html",
        {"site_url": SITE_URL, "url": url, "email": userprofile.email},
    )
    message = EmailMultiAlternatives(to=[userprofile.email], subject=subject, body=text_content)
    message.attach_alternative(html_content, "text/html")
    message.send()


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
        url=urljoin(SITE_URL, event.get_absolute_url()),
    )
    html_content = render_to_string(
        "core/mails/new_event.html", {"event": event, "site_url": SITE_URL}
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
