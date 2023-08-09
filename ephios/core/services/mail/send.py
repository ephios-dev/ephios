import logging

from css_inline import css_inline
from django.conf import settings
from django.core.mail import SafeMIMEMultipart, SafeMIMEText

from ephios.core.services.mail.cid import (
    CustomEmail,
    attach_cid_images,
    replace_images_with_cid_paths,
)

logger = logging.getLogger(__name__)


def send_mail(
    to,
    subject,
    plaintext,
    html=None,
    from_email=None,
    cc=None,
    bcc=None,
    is_autogenerated=True,
):
    headers = {}
    if is_autogenerated:
        headers["Auto-Submitted"] = "auto-generated"
        # https://learn.microsoft.com/en-us/openspecs/exchange_server_protocols/ms-oxcmail/ced68690-498a-4567-9d14-5c01f974d8b1
        headers["X-Auto-Response-Suppress"] = "OOF, NRN, AutoReply, RN"

    email = CustomEmail(
        to=to,
        subject=subject,
        body=prepare_plaintext(plaintext),
        headers=headers,
        from_email=from_email or settings.DEFAULT_FROM_EMAIL,
        cc=cc,
        bcc=bcc,
    )
    if html:
        html_part = prepare_html_part(html)
        email.attach_alternative(html_part, "multipart/related")
    email.send()


def prepare_plaintext(plaintext):
    """
    Prepare the given plaintext for inclusion in the email.
    * Replace newlines with CRLF
    """
    return plaintext.replace("\n", "\r\n")


def prepare_html_part(html):
    """
    Transform the given rendered HTML into a multipart/related MIME part.
    * Inline CSS
    * replace image URLs with cid: URLs
    """
    inliner = css_inline.CSSInliner()
    html = inliner.inline(html)
    html_part = SafeMIMEMultipart(_subtype="related", encoding=settings.DEFAULT_CHARSET)
    cid_html, cid_images = replace_images_with_cid_paths(html)
    html_part.attach(SafeMIMEText(cid_html, "html", settings.DEFAULT_CHARSET))
    attach_cid_images(html_part, cid_images, verify_ssl=True)
    return html_part
