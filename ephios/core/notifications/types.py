from urllib.parse import urljoin

from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from ephios.core.models import UserProfile
from ephios.core.models.users import Notification
from ephios.core.signals import register_notification_types


def all_notification_types():
    for _, handlers in register_notification_types.send(None):
        yield from (h() for h in handlers)


def notification_type_from_slug(slug):
    for notification in all_notification_types():
        if notification.slug == slug:
            return notification
    raise ValueError(_("Notification type '{slug}' was not found.").format(slug=slug))


class AbstractNotificationHandler:
    @property
    def slug(self):
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
    slug = "ephios.profile_update"

    @classmethod
    def create(cls, user: UserProfile):
        return Notification.objects.create(slug=cls.slug, user=user)

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
