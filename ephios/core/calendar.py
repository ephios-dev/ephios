from calendar import LocaleHTMLCalendar
from datetime import date
from itertools import groupby


class ShiftCalendar(LocaleHTMLCalendar):
    cssclass_month = "table table-fixed"

    def __init__(self, shifts, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shifts = self.group_by_day(shifts)

    def formatmonth(self, theyear, themonth, withyear=True):
        self.year, self.month = theyear, themonth
        return super().formatmonth(theyear, themonth)

    def group_by_day(self, shifts):
        return dict(
            [
                (day, list(items))
                for day, items in groupby(shifts, lambda shift: shift.start_time.date().day)
            ]
        )

    def formatday(self, day, weekday):
        if day != 0:
            cssclass = self.cssclasses[weekday]
            if date.today() == date(self.year, self.month, day):
                cssclass += " today"
            if day in self.shifts:
                cssclass += " filled"
                body = ["<br />"]
                for shift in self.shifts[day]:
                    body.append('<a href="%s">' % shift.event.get_absolute_url())
                    body.append(shift.event.title)
                    body.append("</a><br />")
                return self.day_cell(cssclass, "%d %s" % (day, "".join(body)))
            return self.day_cell(cssclass, day)
        return self.day_cell("noday", "&nbsp;")

    def day_cell(self, cssclass, body):
        return '<td class="calendar-row-height p-1 break-word %s">%s</td>' % (cssclass, body)
