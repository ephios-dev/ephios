import logging
import os
import re
from email.mime.image import MIMEImage
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from django.core.mail import EmailMultiAlternatives, SafeMIMEMultipart

from ephios.core.templatetags.settings_extras import make_absolute

logger = logging.getLogger(__name__)


# The following code is based on the pretix implementation [source]
# for embedding cid images in emails.
# It is released under the Apache License 2.0.
# If you did not receive a copy of the license, please refer to
# https://www.apache.org/licenses/LICENSE-2.0.html
#
# source:
# https://github.com/pretix/pretix/blob/a08272571b7b67a3f41e02cf05af8183e3f94a02/src/pretix/base/services/mail.py


class CustomEmail(EmailMultiAlternatives):
    def _create_mime_attachment(self, content, mimetype):
        """
        Convert the content, mimetype pair into a MIME attachment object.

        If the mimetype is message/rfc822, content may be an
        email.Message or EmailMessage object, as well as a str.
        """
        basetype, subtype = mimetype.split("/", 1)
        if basetype == "multipart" and isinstance(content, SafeMIMEMultipart):
            return content
        return super()._create_mime_attachment(content, mimetype)


def replace_images_with_cid_paths(body_html):
    if body_html:
        email = BeautifulSoup(body_html, "lxml")
        cid_images = []
        for image in email.findAll("img"):
            original_image_src = image["src"]
            try:
                cid_id = "image_%s" % cid_images.index(original_image_src)
            except ValueError:
                cid_images.append(original_image_src)
                cid_id = "image_%s" % (len(cid_images) - 1)
            image["src"] = "cid:%s" % cid_id
        return str(email), cid_images
    else:
        return body_html, []


def attach_cid_images(msg, cid_images, verify_ssl=True):
    if cid_images and len(cid_images) > 0:
        msg.mixed_subtype = "mixed"
        for key, image in enumerate(cid_images):
            cid = "image_%s" % key
            try:
                mime_image = convert_image_to_cid(image, cid, verify_ssl)
                if mime_image:
                    msg.attach(mime_image)
            except:
                logger.exception("ERROR attaching CID image %s[%s]" % (cid, image))


def encoder_linelength(msg):
    """
    RFC1341 mandates that base64 encoded data may not be longer than 76 characters per line
    https://www.w3.org/Protocols/rfc1341/5_Content-Transfer-Encoding.html section 5.2
    """
    orig = msg.get_payload(decode=True).replace(b"\n", b"").replace(b"\r", b"")
    max_length = 76
    pieces = []
    for i in range(0, len(orig), max_length):
        chunk = orig[i : i + max_length]
        pieces.append(chunk)
    msg.set_payload(b"\r\n".join(pieces))


def convert_image_to_cid(image_src, cid_id, verify_ssl=True):
    image_src = image_src.strip()
    try:
        if image_src.startswith("data:image/"):
            image_type, image_content = image_src.split(",", 1)
            image_type = re.findall(r"data:image/(\w+);base64", image_type)[0]
            mime_image = MIMEImage(image_content, _subtype=image_type, _encoder=encoder_linelength)
            mime_image.add_header("Content-Transfer-Encoding", "base64")
        elif image_src.startswith("data:"):
            logger.exception("ERROR creating MIME element %s[%s]" % (cid_id, image_src))
            return None
        else:
            # replaced normalize_image_url with these two lines
            if "://" not in image_src:
                image_src = make_absolute(image_src)
            path = urlparse(image_src).path
            guess_subtype = os.path.splitext(path)[1][1:]
            response = requests.get(image_src, verify=verify_ssl)
            mime_image = MIMEImage(response.content, _subtype=guess_subtype)
        mime_image.add_header("Content-ID", "<%s>" % cid_id)
        return mime_image
    except:
        logger.exception("ERROR creating mime_image %s[%s]" % (cid_id, image_src))
        return None
