import datetime
import itertools
from functools import reduce

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


def format_anything(value):
    """Return some built-in types in a human readable way."""
    if isinstance(value, bool):
        return yesno(value)
    if isinstance(value, datetime.datetime):
        return formats.date_format(value, format="SHORT_DATETIME_FORMAT")
    if isinstance(value, models.QuerySet):
        return ", ".join(str(e) for e in value)
    if value is None:
        return _("None")
    return str(value)


def dotted_get(dictionary, path, default=None):
    """
    Get a value from a nested dict by dotted path notation.
    """
    return (
        reduce(
            lambda d, key: d.get(key, None) if isinstance(d, dict) else None,
            path.split("."),
            dictionary,
        )
        or default
    )
