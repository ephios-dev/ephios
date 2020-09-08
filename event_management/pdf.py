import io

import pytz
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import formats
from reportlab.lib.pagesizes import A5, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, Spacer
from django.utils.translation import gettext as _

from event_management.models import Event
from jep import settings


def event_detail_pdf(request, *args, **kwargs):
    event = get_object_or_404(Event, **kwargs)

    if event.shifts.count() > 1:
        ...
    else:
        return _single_shift_event_pdf(event)


def _single_shift_event_pdf(event):
    buffer = io.BytesIO()

    landscape(A5)
    style = getSampleStyleSheet()
    story = [
        Paragraph(f"{event.type}: {event.title}", style["Heading1"]),
        Spacer(height=0.5 * cm, width=15 * cm),
    ]

    shift = event.shifts.first()
    tz = pytz.timezone(settings.TIME_ZONE)
    start_time = shift.start_time.astimezone(tz)
    data = (
        [
            [_("Location"), event.location],
            [
                _("Date"),
                f"{formats.date_format(start_time, 'l')}, {formats.date_format(start_time, 'SHORT_DATE_FORMAT')}",
            ],
            [
                _("Time"),
                f"{formats.time_format(start_time)} - {formats.time_format(shift.end_time.astimezone(tz))}",
            ],
            [_("Meeting time"), formats.time_format(shift.meeting_time.astimezone(tz))],
        ]
        + [[key, value] for key, value in shift.signup_method.get_signup_info().items()]
        + [[_("Description"), Paragraph(event.description)]]
    )
    table = Table(data, colWidths=[3.7 * cm, 9 * cm])
    table.setStyle([("VALIGN", (0, -1), (-1, -1), "TOP")])
    story.append(table)
    story.append(Spacer(height=0.5 * cm, width=15 * cm))

    story.append(Paragraph(_("Participants"), style["Heading2"]))
    data = [
        [f"{participator.first_name} {participator.last_name}"]
        for participator in shift.get_participators()
    ]
    story.append(Table(data, colWidths=[12.7 * cm]))

    p = SimpleDocTemplate(
        buffer,
        pagesize=A5,
        title=event.title,
        leftMargin=1 * cm,
        rightMargin=1 * cm,
        topMargin=1 * cm,
        bottomMargin=1 * cm,
    )
    p.build(story)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"{event.title}.pdf")
