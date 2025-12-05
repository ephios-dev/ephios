import datetime
import json
from calendar import monthrange

from dateutil.relativedelta import relativedelta
from django.db import models
from django.utils.translation import gettext as _


class RelativeTime:
    """
    Represents a relative time duration.
    """

    def __init__(self, years=None, months=None, days=None, **kwargs):
        self.years = years
        self.months = months
        self.days = days

    def to_json(self):
        return {"years": self.years, "months": self.months, "days": self.days}

    @classmethod
    def from_json(cls, data):
        if not data:
            return cls()
        if isinstance(data, str):
            data = json.loads(data)
        return cls(**data)

    def apply_to(self, base_date: datetime.date):
        target_date = base_date + relativedelta(years=self.years)
        if self.days and self.months:
            target_date = target_date.replace(month=self.months)
            last_day = monthrange(target_date.year, self.months)[1]
            target_day = min(self.days, last_day)
            target_date = target_date.replace(day=target_day)
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
