from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext as _

from ephios.settings import SITE_URL


def send_account_creation_info(userprofile):
    subject = _("Welcome to ephios!")
    uid = urlsafe_base64_encode(force_bytes(userprofile.id))
    token = default_token_generator.make_token(userprofile)
    reset_link = reverse("password_reset_confirm", kwargs={"uidb64": uid, "token": token})
    text_content = _(
        "You're receiving this email because a new account has been created for you at ephios.\n"
        "Please go to the following page and choose a password: {url}{reset_link}\n"
        "Your username is your email address: {email}\n"
    ).format(url=SITE_URL, reset_link=reset_link, email=userprofile.email)

    html_content = render_to_string(
        "user_management/new_account_email.html",
        {"uid": uid, "token": token, "site_url": SITE_URL, "email": userprofile.email},
    )
    message = EmailMultiAlternatives(to=[userprofile.email], subject=subject, body=text_content)
    message.attach_alternative(html_content, "text/html")
    message.send()


def send_account_update_info(userprofile):
    subject = _("ephios account updated")
    url = reverse("user_management:profile")
    text_content = _(
        "You're receiving this email because your account at ephios has been updated.\n"
        "You can see the changes in your profile: {site_url}{url}\n"
        "Your username is your email address: {email}\n"
    ).format(site_url=SITE_URL, url=url, email=userprofile.email)

    html_content = render_to_string(
        "user_management/account_updated_email.html",
        {"site_url": SITE_URL, "url": url, "email": userprofile.email},
    )
    message = EmailMultiAlternatives(to=[userprofile.email], subject=subject, body=text_content)
    message.attach_alternative(html_content, "text/html")
    message.send()
