import io

from django.http import FileResponse
from django.utils import formats
from django.utils.timezone import get_default_timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic.detail import SingleObjectMixin
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ephios.core.models import AbstractParticipation, Event
from ephios.extra.mixins import CustomPermissionRequiredMixin


class BasePDFExporter:
    def __init__(self, title, style=getSampleStyleSheet(), pagesize=A4):
        self.title = title
        self.style = style
        self.pagesize = pagesize
        self.margin = 15 * mm

    @property
    def content_width(self):
        return self.pagesize[0] - 2 * self.margin

    def get_pdf(self):
        buffer = io.BytesIO()
        story = self.get_story()
        p = SimpleDocTemplate(
            buffer,
            pagesize=self.pagesize,
            title=self.title,
            leftMargin=self.margin,
            rightMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin,
        )
        p.build(story)
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename=f"{self.title}.pdf")

    def get_story(self):
        return NotImplemented


class EventExport(BasePDFExporter):
    def get_shift_structure_data_table(self, shift):
        participation_data = shift.structure.get_list_export_data()
        col_count = 3
        rows = [
            [
                _("Name"),
                _("Qualifications"),
                _("Description"),
            ]
        ]
        table_style = [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
        for entry in participation_data:
            p: AbstractParticipation = entry["participation"]
            if p and p.state not in AbstractParticipation.States.REQUESTED_AND_CONFIRMED:
                continue

            name_style = None
            if p and p.state == AbstractParticipation.States.REQUESTED:
                name_style = ParagraphStyle(
                    "CustomStyle", parent=self.style["Normal"], textColor=HexColor("#aa8409")
                )
            description = entry["description"]
            if qualification_string := ", ".join([
                q.abbreviation for q in entry["required_qualifications"]
            ]):
                description += f" ({qualification_string})" if description else qualification_string

            rows.append([
                Paragraph(p.participant.display_name, style=name_style) if p else "",
                (
                    Paragraph(
                        ", ".join(
                            p.participant.qualifications
                            .filter(
                                category__show_with_user=True,
                            )
                            .order_by("category", "title")
                            .values_list("abbreviation", flat=True)
                        )
                    )
                    if p
                    else ""
                ),
                Paragraph(description),
            ])
        table = Table(
            rows,
            hAlign="LEFT",
            colWidths=[self.content_width / col_count] * col_count,
        )
        table.setStyle(
            TableStyle(
                [
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
                    ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
                ]
                + table_style
            )
        )
        return table


class SingleShiftEventExporter(EventExport):
    def __init__(self, event, **kwargs):
        self.event = event
        super().__init__(title=event.title)

    def get_story(self):
        story = [
            Paragraph(f"{self.event.type}: {self.event.title}", self.style["Heading1"]),
            Spacer(height=0.5 * cm, width=15 * cm),
        ]

        shift = self.event.shifts.first()
        tz = get_default_timezone()
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
                for key, value in shift.structure.get_signup_info().items()
            ]
            + [[_("Description"), Paragraph(self.event.description)]]
        )
        table = Table(data, colWidths=[6 * cm, self.content_width - 6 * cm])
        table.setStyle([("VALIGN", (0, 0), (-1, -1), "TOP")])
        story.append(table)
        story.append(Spacer(height=0.5 * cm, width=15 * cm))
        story.append(Paragraph(_("Participants"), self.style["Heading2"]))
        story.append(self.get_shift_structure_data_table(shift))
        return story


class MultipleShiftEventExporter(EventExport):
    def __init__(self, event):
        self.event = event
        super().__init__(title=event.title)

    def get_story(self):
        story = [
            Paragraph(f"{self.event.type}: {self.event.title}", self.style["Heading1"]),
            Spacer(height=0.5 * cm, width=19 * cm),
        ]

        tz = get_default_timezone()
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
        table = Table(data, colWidths=[6 * cm, self.content_width - 6 * cm])
        table.setStyle([("VALIGN", (0, -1), (-1, -1), "TOP")])
        story.append(table)

        for shift in self.event.shifts.all():
            story.append(Spacer(height=1 * cm, width=19 * cm))
            story.append(Paragraph(shift.get_datetime_display(), self.style["Heading2"]))
            data = [
                [_("Meeting time"), formats.time_format(shift.meeting_time.astimezone(tz))],
            ] + [
                [Paragraph(key), Paragraph(value)]
                for key, value in shift.structure.get_signup_info().items()
            ]
            story.append(Table(data, colWidths=[6 * cm, self.content_width - 6 * cm]))
            story.append(Paragraph(_("Participants"), self.style["Heading3"]))
            story.append(self.get_shift_structure_data_table(shift))
        return story


class EventDetailPDFView(CustomPermissionRequiredMixin, SingleObjectMixin, View):
    permission_required = "core.view_event"
    model = Event

    def get(self, request, *args, **kwargs):
        event = self.get_object()
        if event.shifts.count() > 1:
            return MultipleShiftEventExporter(event=event).get_pdf()
        return SingleShiftEventExporter(event=event).get_pdf()
