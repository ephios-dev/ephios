import pprint
import traceback

from django.core.mail import mail_admins
from django.db import models


def report_exception(logger, e, message: str, object=None):
    text = message
    if object is not None:
        text += "\n"
        if isinstance(object, models.Model):
            text += f"{type(object)!s} #{object.pk}: "
        text += pprint.pformat(object)

    text += f"\n{traceback.format_exc()}"
    mail_admins(message, text)
    logger.warning(text)
