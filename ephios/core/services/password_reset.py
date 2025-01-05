import logging

from django.contrib.auth.password_validation import MinimumLengthValidator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.translation import gettext as _

from ephios.core.dynamic import dynamic_settings

logger = logging.getLogger(__name__)


class CustomMinimumLengthValidator(MinimumLengthValidator):
    def password_changed(self, password, user):
        if user is not None:
            # revoke API tokens
            for token in user.api_accesstoken.all():
                token.revoke()

            # send notification to user
            text_content = _(
                "Your password for {site} has been changed. If you didn't request this change, contact an administrator immediately."
            ).format(site=dynamic_settings.SITE_URL)
            html_content = render_to_string(
                "core/mails/base.html",
                {
                    "subject": _("Your {platform} password has been changed").format(
                        platform=dynamic_settings.PLATFORM_NAME
                    ),
                    "body": text_content,
                },
            )
            message = EmailMultiAlternatives(
                to=[user.email],
                subject=_("Your password has been changed"),
                body=text_content,
            )
            message.attach_alternative(html_content, "text/html")
            message.send()
