from datetime import datetime

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import make_aware
from django.utils.translation import gettext as _
from guardian.shortcuts import assign_perm

from ephios.core.models import Event, EventType, Shift, UserProfile


def create_objects():
    admin_user = UserProfile(
        email="admin@localhost",
        display_name="Admin Localhost",
        date_of_birth=datetime(year=1970, month=1, day=1),
    )
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.password = make_password("admin")
    admin_user.save()

    from django.contrib.auth.models import Group

    volunteers = Group.objects.create(name=_("Volunteers"))
    volunteers.user_set.add(admin_user)
    volunteers.save()

    planners = Group.objects.create(name=_("Planners"))
    planners.user_set.add(admin_user)
    planners.save()

    managers = Group.objects.create(name=_("Managers"))
    managers.user_set.add(admin_user)
    managers.save()

    assign_perm("publish_event_for_group", planners, volunteers)
    assign_perm("core.add_event", planners)
    assign_perm("core.delete_event", planners)
    assign_perm("core.view_userprofile", managers)
    assign_perm("core.add_userprofile", managers)
    assign_perm("core.change_userprofile", managers)
    assign_perm("core.delete_userprofile", managers)
    assign_perm("auth.view_group", managers)
    assign_perm("auth.add_group", managers)
    assign_perm("auth.change_group", managers)
    assign_perm("auth.delete_group", managers)

    service_type = EventType.objects.create(title=_("Service"))
    EventType.objects.create(title=_("Training"))

    user = UserProfile(
        email="user@localhost",
        display_name="User Localhost",
        date_of_birth=datetime(year=1970, month=1, day=1),
    )
    user.password = make_password("user")
    user.save()
    volunteers.user_set.add(user)

    event = Event.objects.create(
        title="Concert Medical Service",
        description="Your contact is Lisa Example. Her Phone number is 012345678910",
        type=service_type,
        location="Town Square Gardens",
        active=True,
    )

    assign_perm("core.view_event", volunteers, event)

    Shift.objects.create(
        event=event,
        meeting_time=make_aware(datetime(2043, 6, 30, 15, 30)),
        start_time=make_aware(datetime(2043, 6, 30, 16, 0)),
        end_time=make_aware(datetime(2043, 7, 1, 1, 0)),
        signup_flow_slug="instant_confirmation",
        signup_flow_configuration={
            "signup_until": make_aware(datetime(2043, 6, 29, 8, 0)),
        },
        structure_slug="uniform",
        structure_configuration={
            "minimum_age": 18,
        },
    )


class Command(BaseCommand):
    help = "Load some data for development"

    def handle(self, *args, **options):
        if UserProfile.objects.exists():
            self.stdout.write("WARNING! User objects already exist in your database.")
            if input("Are you sure you want to continue? (yes/no) ") != "yes":
                self.stdout.write("Aborting...")
                return
        with transaction.atomic():
            create_objects()
        self.stdout.write(self.style.SUCCESS("Done."))
