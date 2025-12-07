import datetime
import json
import re
from calendar import monthrange

from dateutil.relativedelta import relativedelta
from django.db import models
from django.utils.translation import gettext as _


class RelativeTime:
    """
    Represents a relative time duration.
    """

    def __init__(self, year=None, month=None, day=None, **kwargs):
        self.year = year
        self.month = month
        self.day = day

    def to_json(self):
        return {"year": self.year, "month": self.month, "day": self.day}

    @classmethod
    def from_json(cls, data):
        if not data:
            return cls()
        if isinstance(data, str):
            data = json.loads(data)
        return cls(**data)

    def apply_to(self, base_date: datetime.date):
        if not (self.year or self.month or self.day):
            return None
        target_date = base_date
        if self.year:
            if type(self.year) is int:
                target_date = target_date.replace(year=self.year)
            elif match := re.match(r"^\+(\d+)$", self.year):
                target_date = target_date + relativedelta(years=int(match.group(0)))
        if self.month:
            if type(self.month) is int and 1 <= self.month <= 12:
                target_date = target_date.replace(month=self.month)
            elif (match := re.match(r"^\+(\d+)$", self.month)) and (
                target_month := int(match.group(0))
            ) < 12:
                target_date = target_date + relativedelta(month=target_month)
        if self.day:
            last_day = monthrange(target_date.year, target_date.month)[1]
            if type(self.day) is int:
                target_date = target_date.replace(day=min(self.day, last_day))
            elif (match := re.match(r"^\+(\d+)$", self.day)) and (
                target_day := int(match.group(0))
            ) < last_day:
                target_date = target_date + relativedelta(day=target_day)
        return target_date


class RelativeTimeModelField(models.JSONField):
    """
    Stores a RelativeTime object as JSON.
    """

    description = _("Relative Time")

    def from_db_value(self, value, expression, connection):
        if value is None:
            return None
        return RelativeTime.from_json(value)

    def to_python(self, value):
        return value.to_json()

    def formfield(self, **kwargs):
        from ephios.extra.fields import RelativeTimeField

        defaults = {"form_class": RelativeTimeField}
        defaults.update(kwargs)
        return super().formfield(**defaults)
