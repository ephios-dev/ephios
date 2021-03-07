from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django_ical.views import ICalFeed
from guardian.shortcuts import get_users_with_perms
from icalendar import vCalAddress

from ephios.core.models import AbstractParticipation, Shift


class EventFeed(ICalFeed):
    file_name = "events.ics"
    timezone = "UTC"
    product_id = "-//ephios//ephios//EN"

    def items(self):
        return Shift.objects.all().filter(event__active=True).order_by("meeting_time")

    def item_title(self, item):
        return item.event.title

    def item_description(self, item):
        return item.event.description

    def item_start_datetime(self, item):
        return item.meeting_time

    def item_end_datetime(self, item):
        return item.end_time

    def item_link(self, item):
        return item.event.get_absolute_url()

    def item_location(self, item):
        return item.event.location

    def item_guid(self, item):
        return f"{item.pk}@{settings.SITE_URL}"

    def item_organizer(self, item):
        user = get_users_with_perms(item.event, only_with_perms_in=["change_event"]).first()
        email = user.email if user else ""
        return vCalAddress(f"MAILTO:{email}")


class UserEventFeed(EventFeed):
    def __init__(self, user):
        super().__init__()
        self.user = user

    def items(self):
        return self.user.get_shifts(
            with_participation_state_in=[AbstractParticipation.States.CONFIRMED]
        )


def user_event_feed_view(request, *args, **kwargs):
    feed = UserEventFeed(get_object_or_404(get_user_model(), **kwargs))
    return feed(request, *args, **kwargs)
