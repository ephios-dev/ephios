from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django_ical.views import ICalFeed
from guardian.shortcuts import get_users_with_perms
from icalendar import vCalAddress

from ephios.core.dynamic import dynamic_settings
from ephios.core.models import AbstractParticipation, Shift
from ephios.extra.auth import access_exempt


class EventFeed(ICalFeed):
    file_name = "events.ics"
    timezone = "UTC"
    product_id = "-//ephios//ephios//EN"

    def items(self):
        return Shift.objects.all().filter(event__active=True).order_by("meeting_time")

    def item_title(self, item):
        if item.label:
            return f"{item.label} ({item.event.title})"
        return item.event.title

    def item_description(self, item):
        return item.event.description

    def item_start_datetime(self, item):
        return item.meeting_time

    def item_end_datetime(self, item):
        return item.end_time

    def item_link(self, item):
        return item.get_absolute_url()

    def item_location(self, item):
        return item.event.location

    def item_guid(self, item):
        return f"{item.pk}@{dynamic_settings.SITE_URL}"

    def item_organizer(self, item):
        user = get_users_with_perms(item.event, only_with_perms_in=["change_event"]).first()
        email = user.email if user else ""
        return vCalAddress(f"MAILTO:{email}")


class UserEventFeed(EventFeed):
    def item_start_datetime(self, item):
        return item.participations.all()[0].start_time

    def item_end_datetime(self, item):
        return item.participations.all()[0].end_time

    def item_status(self, item):
        # The ical status field can be CONFIRMED|TENTATIVE|CANCELLED
        return {
            AbstractParticipation.States.CONFIRMED: "CONFIRMED",
            AbstractParticipation.States.REQUESTED: "TENTATIVE",  # displayed less opaque in many calendars
            AbstractParticipation.States.RESPONSIBLE_REJECTED: "CANCELLED",  # often displayed struck out
        }[item.participations.all()[0].state]

    def items(self):
        shift_ids = self.user.participations.filter(
            state__in=self.include_participation_states,
        ).values_list("shift", flat=True)
        return (
            Shift.objects
            .filter(pk__in=shift_ids)
            .select_related("event")
            .prefetch_related(Prefetch("participations", queryset=self.user.participations.all()))
        )

    def __init__(
        self, user, include_participation_states=(AbstractParticipation.States.CONFIRMED,)
    ):
        super().__init__()
        self.user = user
        self.include_participation_states = include_participation_states


@access_exempt
def user_event_feed_view(request, *args, **kwargs):
    include_participation_states = [AbstractParticipation.States.CONFIRMED]
    if (r := request.GET.get("requested")) and r != "0":
        include_participation_states.append(AbstractParticipation.States.REQUESTED)
    if (r := request.GET.get("rejected")) and r != "0":
        include_participation_states.append(AbstractParticipation.States.RESPONSIBLE_REJECTED)
    feed = UserEventFeed(
        get_object_or_404(get_user_model(), **kwargs),
        include_participation_states=include_participation_states,
    )
    return feed(request, *args, **kwargs)
