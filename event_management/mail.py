from django.core import mail
from django.core.mail import EmailMultiAlternatives, EmailMessage
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template import Template, Context
from django.template.loader import get_template, render_to_string
from guardian.shortcuts import get_users_with_perms

from event_management.models import AbstractParticipation, LocalParticipation
from jep.permissions import get_groups_with_perms
from jep.settings import SITE_URL
from user_management.models import UserProfile
from django.utils.translation import gettext as _


def new_event(event):
    messages = []
    users = UserProfile.objects.filter(
        groups__in=get_groups_with_perms(event, only_with_perms_in=["view_event"])
    ).distinct()
    responsible_persons = get_users_with_perms(
        event, only_with_perms_in=["change_event"]
    ).distinct()
    responsible_persons_mails = list(responsible_persons.values_list("email", flat=True))

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


@receiver(post_save, sender=LocalParticipation)
def participation_state_changed(sender, **kwargs):
    instance = kwargs["instance"]
    if instance.state != AbstractParticipation.USER_DECLINED:
        EmailMessage(
            to=[instance.user.email],
            subject=_("Your participation state changed"),
            body=_(
                "The status for your participation for the shift {shift} has changed. It is now {status}."
            ).format(shift=instance.shift, status=instance.get_state_display()),
        ).send()
