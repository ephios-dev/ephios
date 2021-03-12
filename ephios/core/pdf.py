import io

import pytz
from django.conf import settings
from django.http import FileResponse
from django.utils import formats
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic.detail import SingleObjectMixin
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, A5
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ephios.core.models import Event
from ephios.extra.mixins import CustomPermissionRequiredMixin


class BasePDFExporter:
    def __init__(self, title, style=getSampleStyleSheet(), pagesize=A4):
        self.title = title
        self.style = style
        self.pagesize = pagesize

    def get_pdf(self):
        buffer = io.BytesIO()
        story = self.get_story()
        p = SimpleDocTemplate(
            buffer,
            pagesize=self.pagesize,
            title=self.title,
            leftMargin=1 * cm,
            rightMargin=1 * cm,
            topMargin=1 * cm,
            bottomMargin=1 * cm,
        )
        p.build(story)
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename=f"{self.title}.pdf")

    def get_story(self):
        return NotImplemented


class SingleShiftEventExporter(BasePDFExporter):
    def __init__(self, event, **kwargs):
        self.event = event
        super().__init__(title=event.title, pagesize=A5)

    def get_story(self):
        story = [
            Paragraph(f"{self.event.type}: {self.event.title}", self.style["Heading1"]),
            Spacer(height=0.5 * cm, width=15 * cm),
        ]

        shift = self.event.shifts.first()
        tz = pytz.timezone(settings.TIME_ZONE)
        start_time = shift.start_time.astimezone(tz)
        data = (
            [
                [_("Location"), self.event.location],
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
            + [
                [Paragraph(key), Paragraph(value)]
                for key, value in shift.signup_method.get_signup_info().items()
            ]
            + [[_("Description"), Paragraph(self.event.description)]]
        )
        table = Table(data, colWidths=[5.7 * cm, 7 * cm])
        table.setStyle([("VALIGN", (0, -1), (-1, -1), "TOP")])
        story.append(table)
        story.append(Spacer(height=0.5 * cm, width=15 * cm))

        if participation_info := shift.signup_method.get_participation_display():
            story.append(Paragraph(_("Participants"), self.style["Heading2"]))
            col_count = len(participation_info[0])
            table = Table(
                [
                    [[Paragraph(entry)] for entry in participation]
                    for participation in participation_info
                ],
                hAlign="LEFT",
                colWidths=[125 * mm / col_count] * col_count,
            )
            table.setStyle(
                TableStyle(
                    [
                        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
                        ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
                    ]
                )
            )
            story.append(table)

        return story


class MultipleShiftEventExporter(BasePDFExporter):
    def __init__(self, event):
        self.event = event
        super().__init__(title=event.title)

    def get_story(self):
        story = [
            Paragraph(f"{self.event.type}: {self.event.title}", self.style["Heading1"]),
            Spacer(height=0.5 * cm, width=19 * cm),
        ]

        tz = pytz.timezone(settings.TIME_ZONE)
        start_time = self.event.get_start_time().astimezone(tz)
        end_time = self.event.get_end_time().astimezone(tz)
        end_date = (
            f"- {formats.date_format(end_time, 'l')}, {formats.date_format(end_time, 'SHORT_DATE_FORMAT')}"
            if end_time.date() > start_time.date()
            else ""
        )
        event_date = f"{formats.date_format(start_time, 'l')}, {formats.date_format(start_time, 'SHORT_DATE_FORMAT')} {end_date}"
        data = [
            [_("Location"), self.event.location],
            [_("Date"), event_date],
            [_("Description"), Paragraph(self.event.description)],
        ]
        table = Table(data, colWidths=[6 * cm, 13 * cm])
        table.setStyle([("VALIGN", (0, -1), (-1, -1), "TOP")])
        story.append(table)

        for shift in self.event.shifts.all():
            story.append(Spacer(height=1 * cm, width=19 * cm))
            story.append(Paragraph(shift.get_start_end_time_display(), self.style["Heading2"]))
            data = [
                [_("Meeting time"), formats.time_format(shift.meeting_time.astimezone(tz))],
            ] + [
                [Paragraph(key), Paragraph(value)]
                for key, value in shift.signup_method.get_signup_info().items()
            ]
            story.append(Table(data, colWidths=[6 * cm, 13 * cm]))

            if participation_info := shift.signup_method.get_participation_display():
                story.append(Paragraph(_("Participants"), self.style["Heading3"]))
                col_count = len(participation_info[0])
                table = Table(
                    [
                        [[Paragraph(entry)] for entry in participation]
                        for participation in participation_info
                    ],
                    hAlign="LEFT",
                    colWidths=[185 * mm / col_count] * col_count,
                )
                table.setStyle(
                    TableStyle(
                        [
                            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
                            ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
                        ]
                    )
                )
                story.append(table)

        return story


class EventDetailPDFView(CustomPermissionRequiredMixin, SingleObjectMixin, View):
    permission_required = "core.view_event"
    model = Event

    def get(self, request, *args, **kwargs):
        event = self.get_object()
        if event.shifts.count() > 1:
            return MultipleShiftEventExporter(event=event).get_pdf()
        return SingleShiftEventExporter(event=event).get_pdf()
