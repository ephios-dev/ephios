import datetime
import itertools

from django.db import models
from django.template.defaultfilters import yesno
from django.utils import formats
from django.utils.translation import gettext_lazy as _


def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


def format_anything(value):
    """Return some inbuilt types in a human readable way."""
    if isinstance(value, bool):
        return yesno(value)
    if isinstance(value, datetime.datetime):
        return formats.date_format(value, format="SHORT_DATETIME_FORMAT")
    if isinstance(value, models.Model):
        return str(value)
    if isinstance(value, models.Model):
        return str(value)
    if isinstance(value, models.QuerySet):
        return ", ".join(str(e) for e in value)
    if value is None:
        return _("None")
    return str(value)
