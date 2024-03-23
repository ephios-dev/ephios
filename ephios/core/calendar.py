from calendar import HTMLCalendar, day_abbr
from datetime import date, datetime
from itertools import groupby

from django.template.loader import render_to_string
from django.utils.formats import date_format
from django.utils.translation import gettext as _


class ShiftCalendar(HTMLCalendar):
    cssclass_month = "table table-fixed"

    def __init__(self, shifts, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shifts = {
            k: list(v) for (k, v) in groupby(shifts, lambda shift: shift.start_time.date().day)
        }
        self.request = request

    def formatmonth(self, theyear, themonth, withyear=True):
        self.year, self.month = theyear, themonth
        return super().formatmonth(theyear, themonth)

    def formatmonthname(self, theyear, themonth, withyear=True):
        dt = datetime(theyear, themonth, 1)
        return f'<tr><th colspan="7" class="month">{date_format(dt, format="b Y")}</th></tr>'

    def formatweekday(self, day):
        return f'<th class="text-center {self.cssclasses[day]}">{_(day_abbr[day])}</th>'

    def formatday(self, day, weekday):
        if day != 0:
            cssclass = self.cssclasses[weekday]
            this_date = date(self.year, self.month, day)
            today = date.today() == this_date
            if day in self.shifts:
                cssclass += " filled"
            content = render_to_string(
                "core/fragments/calendar_day.html",
                {
                    "day": day,
                    "shifts": self.shifts.get(day, None),
                    "today": today,
                    "date": this_date.isoformat(),
                    "request": self.request,
                },
            )
            return self.day_cell(cssclass, content)
        return self.day_cell("noday", "&nbsp;")

    def day_cell(self, cssclass, body):
        return f'<td class="calendar-row-height p-0 pe-1 p-lg-1 {cssclass}">{body}</td>'
