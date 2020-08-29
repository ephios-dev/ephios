from django.contrib.auth.password_validation import MinimumLengthValidator
from django.core.mail import EmailMessage
from django.utils.translation import gettext as _

from jep.settings import SITE_URL


class CustomMinimumLengthValidator(MinimumLengthValidator):
    def password_changed(self, password, user):
        if user is not None:
            EmailMessage(
                to=[user.email],
                subject=_("Your password has been changed"),
                body=_(
                    "Your password for {site} has been changed. If you didn't request this change, contact an administrator immediately."
                ).format(site=SITE_URL),
            ).send()
