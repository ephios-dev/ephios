import datetime
import itertools
import os
import random
import string

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.http import FileResponse, HttpResponse
from django.template.defaultfilters import yesno
from django.utils import formats
from django.utils.translation import gettext_lazy as _

# This file includes some of the itertools recipes from https://docs.python.org/3/library/itertools.html


def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


def partition(pred, iterable):
    "Use a predicate to partition entries into false entries and true entries"
    # partition(is_odd, range(10)) --> 0 2 4 6 8   and  1 3 5 7 9
    t1, t2 = itertools.tee(iterable)
    return itertools.filterfalse(pred, t1), filter(pred, t2)


def format_anything(value):
    """Return some inbuilt types in a human readable way."""
    if isinstance(value, bool):
        return yesno(value)
    if isinstance(value, datetime.datetime):
        return formats.date_format(value, format="SHORT_DATETIME_FORMAT")
    if isinstance(value, models.QuerySet):
        return ", ".join(str(e) for e in value)
    if value is None:
        return _("None")
    return str(value)


def accelerated_media_response(file):
    if settings.FALLBACK_MEDIA_SERVING:
        # use built-in django file serving - only as a fallback as this is slow
        response = FileResponse(file)
    else:
        # use nginx x-accel-redirect for faster file serving
        # nginx needs to be set up to serve files from the media url
        response = HttpResponse()
        response["X-Accel-Redirect"] = file.url
    response["Content-Disposition"] = "attachment; filename=" + os.path.split(file.name)[1]
    return response


def file_ticket(file):
    key = "".join(
        random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(32)
    )
    cache.set(key, file, 60)
    return key
