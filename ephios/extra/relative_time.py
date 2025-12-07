from calendar import calendar
import datetime
import json
from django.db import models
from django.utils.translation import gettext as _
from dateutil.relativedelta import relativedelta


class RelativeTimeTypeRegistry:
    """
    Registry that holds all known relative time types.
    """

    """Global registry for all relative time types."""
    _registry = {}

    @classmethod
    def register(cls, name, handler):
        if not isinstance(handler, type):
            raise TypeError(f"Handler for '{name}' must be a class, got {handler!r}")
        cls._registry[name] = handler
        return handler
    
    @classmethod
    def get(cls, name):
        return cls._registry.get(name)
    
    @classmethod
    def all(cls):
        return cls._registry.items()

class RelativeTime:
    """
    Represents a relative time duration.
    """

    def __init__(self, type="no_expiration", **kwargs):
        self.type = type
        self.params = kwargs

    def __repr__(self):
        return f"RelativeTime(type={self.type}, params={self.params})"
    
    def to_json(self):
        return {"type": self.type, **self.params}
    
    @classmethod
    def from_json(cls, data):
        if not data:
            return cls("no_expiration")
        if isinstance(data, str):
            data = json.loads(data)
        data = data.copy()
        type_ = data.pop("type", "no_expiration")
        return cls(type_, **data)
    
    def apply_to(self, base_time: datetime.date):
        """Delegates to the registered handler."""
        handler = RelativeTimeTypeRegistry.get(self.type)
        if not handler:
            raise ValueError(f"Unknown relative time type: {self.type}")
        return handler.apply(base_time, **self.params)
    
    # decorator
    @classmethod
    def register_type(cls, name):
        def decorator(handler_cls):
            RelativeTimeTypeRegistry.register(name, handler_cls)
            return handler_cls
        return decorator


# ---------------------------------------------------------------------
# Default built-in types
# ---------------------------------------------------------------------

@RelativeTime.register_type("no_expiration")
class NoExpirationType:
    fields = []

    @staticmethod
    def apply(base_date, **kwargs):
        return None

@RelativeTime.register_type("after_x_years")
class AfterXYearsType:
    fields = ["years"]

    @staticmethod
    def apply(base_date, years=0, **kwargs):
        return base_date + relativedelta(years=years)

@RelativeTime.register_type("at_x_y_after_z_years")
class AtXYAfterZYearsType:
    fields = ["day", "month", "years"]

    @staticmethod
    def apply(base_date, day=None, month=None, years=0, **kwargs):
        if not (day and month):
            raise ValueError(_("Day and Month must be provided"))
        target_date = base_date + relativedelta(years=years)
        target_date = target_date.replace(month=month)
        last_day = calendar.monthrange(target_date.year, month)[1]
        target_day = min(day, last_day)
        return target_date.replace(day=target_day)


# ---------------------------------------------------------------------
# ModelField integration
# ---------------------------------------------------------------------

class RelativeTimeModelField(models.JSONField):
    """
    Stores a RelativeTime object as JSON.
    """

    description = _("Relative Time")

    def from_db_value(self, value, expression, connection):
        if value is None:
            return RelativeTime("no_expiration")
        return RelativeTime.from_json(value)
    
    def to_python(self, value):
        if isinstance(value, RelativeTime):
            return value
        if value is None:
            return RelativeTime("no_expiration")
        return RelativeTime.from_json(value)
    
    def get_prep_value(self, value):
        if isinstance(value, RelativeTime):
            return value.to_json()
        if value is None:
            return {"type": "no_expiration"}
        return RelativeTime.from_json(value)
    
    def formfield(self, **kwargs):
        from ephios.extra.fields import RelativeTimeField
        defaults = {'form_class': RelativeTimeField}
        defaults.update(kwargs)
        return super().formfield(**defaults)