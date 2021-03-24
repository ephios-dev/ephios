import logging

from django.conf import settings
from django.contrib.auth.password_validation import MinimumLengthValidator
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext as _

from ephios.core.models import AbstractParticipation

logger = logging.getLogger(__name__)


class CustomMinimumLengthValidator(MinimumLengthValidator):
    def password_changed(self, password, user):
        if user is not None:
            text_content = _(
                "Your password for {site} has been changed. If you didn't request this change, contact an administrator immediately."
            ).format(site=settings.SITE_URL)
            html_content = render_to_string("email_base.html", {"message_text": text_content})
            message = EmailMultiAlternatives(
                to=[user.email],
                subject=_("Your password has been changed"),
                body=text_content,
            )
            message.attach_alternative(html_content, "text/html")
            message.send()


def send_participation_finished(sender, **kwargs):
    """
    This method is registered in signals.py as a receiver of ``periodic_signal``.
    """
    from ephios.core.signals import participation_finished

    relevant_participations = AbstractParticipation.objects.filter(
        state=AbstractParticipation.States.CONFIRMED,
        shift__end_time__lt=timezone.now(),
        finished=False,
    ).select_related("shift", "shift__event")
    for participation in relevant_participations:
        try:
            with transaction.atomic():
                participation_finished.send(None, participation=participation)
                participation.finished = True
                participation.save()
        except Exception:  # pylint: disable=broad-except
            if settings.DEBUG:
                raise
            logger.error("Error while dispatching participation_finished.", exc_info=True)
