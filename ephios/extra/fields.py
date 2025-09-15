import datetime

from django.utils.translation import gettext as _
from django import forms
from django.forms.utils import from_current_timezone
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
    A custom form field that allows selection between two options:
    - 'after_x_years': After X years
    - 'at_xy_after_z_years': For at the X.Y. after Z years
    The value is stored as JSON.
    """

    widget = RelativeTimeWidget

    def bound_data(self, data, initial):
        # If the widget gave us a list, just return it directly
        if isinstance(data, list):
            return data
        return super().bound_data(data, initial)

    def to_python(self, value):
        if not value:
            return None
        
        try:
            if isinstance(value, list):
                choice, day, month, years = value
                
                choice = int(choice) if choice is not None else 0

                if choice == 0:
                    return {
                        "type": "no_expiration"
                    }
                elif choice == 1:
                    return {
                        "type": "after_x_years",
                        "years": int(years) if years is not None else 0
                    }
                elif choice == 2:
                    return {
                        "type": "at_xy_after_z_years",
                        "day": int(day) if day else None,
                        "month": int(month) if month else None,
                        "years": int(years) if years else 0
                    }
                else:
                    raise ValueError(
                        _("Invalid choice")
                    )
            
            if isinstance(value, str):
                data = json.loads(value)
            else:
                data = value  # could already be a dict

            # Validation
            if not isinstance(data, dict):
                raise ValueError("Not a dict")

            if data.get("type") == "after_x_years":
                if not isinstance(data.get("years"), int) or data["years"] < 0:
                    raise ValueError("Invalid years")

            elif data.get("type") == "at_xy_after_z_years":
                if not isinstance(data.get("years"), int) or data["years"] < 0:
                    raise ValueError("Invalid years")
                if not (1 <= int(data.get("day", 0)) <= 31):
                    raise ValueError("Invalid day")
                if not (1 <= int(data.get("month", 0)) <= 12):
                    raise ValueError("Invalid month")

            elif data.get("type") == "no_expiration":
                pass

            else:
                raise ValueError("Invalid type")

            return data
        
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            raise forms.ValidationError(
                _("Invalid format: {error}").format(error=e)
            ) from e
    
    def prepare_value(self, value):
        """
        Ensure the widget always gets a list [choice, day, month, years].
        """
        if value is None:
            return [0, None, None, None]

        # If already a list, just pass it through
        if isinstance(value, list):
            return value

        # If it's a JSON string, parse it
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return [0, None, None, None]

        if not isinstance(value, dict):
            return [0, None, None, None]

        t = value.get("type")
        if t == "no_expiration":
            return [0, None, None, None]
        elif t == "after_x_years":
            return [1, None, None, value.get("years")]
        elif t == "at_xy_after_z_years":
            return [2, value.get("day"), value.get("month"), value.get("years")]

        return [0, None, None, None]