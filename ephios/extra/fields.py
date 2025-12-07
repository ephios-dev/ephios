import datetime

from django.utils.translation import gettext as _
from django import forms
from django.forms.utils import from_current_timezone
from ephios.extra.relative_time import RelativeTimeTypeRegistry
from ephios.extra.widgets import RelativeTimeWidget

import json

class EndOfDayDateTimeField(forms.DateTimeField):
    """
    A datetime form field that when used with a date-only widget
    creates a datetime with the time at the end of the given day.
    """

    def to_python(self, value):
        result = super().to_python(value)
        if result is None:
            return result
        return from_current_timezone(
            datetime.datetime.max.replace(
                year=result.year,
                month=result.month,
                day=result.day,
            )
        )

class RelativeTimeField(forms.JSONField):
    """
    A form field that dynamically adapts to all registered RelativeTime types.
    """

    widget = RelativeTimeWidget

    def bound_data(self, data, initial):
        if isinstance(data, list):
            return data
        return super().bound_data(data, initial)

    def to_python(self, value):
        if not value:
            return None

        try:
            # Determine all known types and their parameters
            type_names = [name for name, _ in RelativeTimeTypeRegistry.all()]

            if isinstance(value, list):
                # first element = type index
                type_index = int(value[0]) if value and value[0] is not None else 0
                type_name = type_names[type_index] if 0 <= type_index < len(type_names) else None
                handler = RelativeTimeTypeRegistry.get(type_name)
                if not handler:
                    raise ValueError(_("Invalid choice"))

                params = {}
                # remaining values correspond to all known parameters
                all_param_names = sorted({p for _, h in RelativeTimeTypeRegistry.all() for p in getattr(h, "fields", [])})
                for param_name, param_value in zip(all_param_names, value[1:]):
                    if param_value not in (None, ""):
                        params[param_name] = int(param_value)
                return {"type": type_name, **params}

            if isinstance(value, str):
                data = json.loads(value)
            else:
                data = value

            if not isinstance(data, dict):
                raise ValueError("Not a dict")

            type_name = data.get("type")
            handler = RelativeTimeTypeRegistry.get(type_name)
            if not handler:
                raise ValueError(_("Unknown type"))

            # basic validation: ensure required params exist
            for param in getattr(handler, "fields", []):
                if param not in data:
                    raise ValueError(_("Missing field: {param}").format(param=param))

            return data

        except (json.JSONDecodeError, ValueError, TypeError) as e:
            raise forms.ValidationError(
                _("Invalid format: {error}").format(error=e)
            ) from e

    def prepare_value(self, value):
        if value is None:
            return [0] + [None] * len({p for _, h in RelativeTimeTypeRegistry.all() for p in getattr(h, "fields", [])})

        if isinstance(value, list):
            return value

        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return [0] + [None] * len({p for _, h in RelativeTimeTypeRegistry.all() for p in getattr(h, "fields", [])})

        if not isinstance(value, dict):
            return [0] + [None] * len({p for _, h in RelativeTimeTypeRegistry.all() for p in getattr(h, "fields", [])})

        type_names = [name for name, _ in RelativeTimeTypeRegistry.all()]
        type_name = value.get("type", "no_expiration")
        type_index = type_names.index(type_name) if type_name in type_names else 0

        all_param_names = sorted({p for _, h in RelativeTimeTypeRegistry.all() for p in getattr(h, "fields", [])})
        params = [value.get(p) for p in all_param_names]

        return [type_index] + params