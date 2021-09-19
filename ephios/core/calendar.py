from calendar import HTMLCalendar, day_abbr
from datetime import date, datetime
from itertools import groupby

from django.utils.formats import date_format
from django.utils.translation import gettext as _


class ShiftCalendar(HTMLCalendar):
    cssclass_month = "table table-fixed"

    def __init__(self, shifts, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shifts = {
            k: list(v) for (k, v) in groupby(shifts, lambda shift: shift.start_time.date().day)
        }

    def formatmonth(self, theyear, themonth, withyear=True):
        self.year, self.month = theyear, themonth
        return super().formatmonth(theyear, themonth)

    def formatmonthname(self, theyear, themonth, withyear=True):
        dt = datetime(theyear, themonth, 1)
        return f'<tr><th colspan="7" class="month">{date_format(dt, format="b Y")}</th></tr>'

    def formatweekday(self, day):
        return f'<th class="{self.cssclasses[day]}">{_(day_abbr[day])}</th>'

    def formatday(self, day, weekday):
        if day != 0:
            cssclass = self.cssclasses[weekday]
            if date.today() == date(self.year, self.month, day):
                cssclass += " calendar-today"
            if day in self.shifts:
                cssclass += " filled"
                body = ["<br />"]
                for shift in self.shifts[day]:
                    body.append(f'<a href="{shift.event.get_absolute_url()}">')
                    body.append(shift.event.title)
                    body.append("</a><br />")
                return self.day_cell(cssclass, f"{day} {''.join(body)}")
            return self.day_cell(cssclass, day)
        return self.day_cell("noday", "&nbsp;")

    def day_cell(self, cssclass, body):
        return f'<td class="calendar-row-height p-1 break-word {cssclass}">{body}</td>'
