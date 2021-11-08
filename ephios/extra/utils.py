import datetime
import itertools

from django.db import models
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
