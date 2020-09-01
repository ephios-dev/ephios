import json
import uuid
from datetime import datetime

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.timezone import make_aware
from guardian.shortcuts import assign_perm
from django.core.serializers.json import DjangoJSONEncoder

from django.utils.translation import gettext as _

from event_management.models import EventType, Event, Shift
from user_management.models import (
    UserProfile,
    QualificationCategory,
    Qualification,
    QualificationGrant,
)

AVAILABLE_DATASET_CLASSES = []


def register_dataset(dataset_type):
    AVAILABLE_DATASET_CLASSES.append(dataset_type)
    return dataset_type


class AbstractDataset:
    identifier = NotImplemented
    action = None

    def __init__(self, command):
        self.stdout = command.stdout

    def create_objects(self, *args, **options):
        self.stdout.write(self.description)

    @property
    def description(self):
        return "\n".join(klaas.action or str(klaas) for klaas in reversed(type(self).__mro__[:-2]))

    def add_arguments(self, parser):
        pass


@register_dataset
class AdminUserDataset(AbstractDataset):
    identifier = "admin_user"
    action = "Add a superuser admin@localhost with password 'admin'."

    def create_objects(self, *args, **options):
        super().create_objects(*args, **options)
        self.admin_user = UserProfile(
            email="admin@localhost",
            first_name="Admin",
            last_name="Localhost",
            date_of_birth=datetime(year=1970, month=1, day=1),
        )
        self.admin_user.is_staff = True
        self.admin_user.is_superuser = True
        self.admin_user.password = make_password("admin")
        self.admin_user.save()


@register_dataset
class DebugDataset(AdminUserDataset):
    identifier = "debug"
    action = "Create a planner and volunteers group and add the superuser and another user to it. Add an event and a few qualifications."

    def create_objects(self, *args, **options):
        super().create_objects(*args, **options)
        from django.contrib.auth.models import Group

        volunteers = Group.objects.create(name=_("Volunteers"))
        volunteers.user_set.add(self.admin_user)
        volunteers.save()

        planners = Group.objects.create(name=_("Planners"))
        planners.user_set.add(self.admin_user)
        planners.save()

        managers = Group.objects.create(name=_("Managers"))
        managers.user_set.add(self.admin_user)
        managers.save()

        assign_perm("publish_event_for_group", planners, volunteers)
        assign_perm("event_management.add_event", planners)
        assign_perm("event_management.delete_event", planners)
        assign_perm("event_management.view_past_event", planners)
        assign_perm("user_management.view_userprofile", managers)
        assign_perm("user_management.add_userprofile", managers)
        assign_perm("user_management.change_userprofile", managers)
        assign_perm("user_management.delete_userprofile", managers)
        assign_perm("auth.view_group", managers)
        assign_perm("auth.add_group", managers)
        assign_perm("auth.change_group", managers)
        assign_perm("auth.delete_group", managers)

        service_type = EventType.objects.create(title=_("Service"), can_grant_qualification=False)
        EventType.objects.create(title=_("Training"), can_grant_qualification=True)

        user = UserProfile(
            email="user@localhost",
            first_name="User",
            last_name="Localhost",
            date_of_birth=datetime(year=1970, month=1, day=1),
        )
        user.password = make_password("user")
        user.save()
        volunteers.user_set.add(user)

        medical_category = QualificationCategory.objects.create(
            title=_("Medical"), uuid=uuid.UUID("50380292-b9c9-4711-b70d-8e03e2784cfb"),
        )

        rs = Qualification.objects.create(
            category=medical_category,
            title="Rettungssanitäter",
            abbreviation="RS",
            uuid=uuid.UUID("0b41fac6-ca9e-4b8a-82c5-849412187351"),
        )

        nfs = Qualification.objects.create(
            category=medical_category,
            title="Notfallsanitäter",
            abbreviation="NFS",
            uuid=uuid.UUID("d114125b-7cf4-49e2-8908-f93e2f95dfb8"),
        )
        nfs.included_qualifications.add(rs)

        QualificationGrant.objects.create(user=user, qualification=nfs)
        QualificationGrant.objects.create(user=self.admin_user, qualification=rs)

        event = Event.objects.create(
            title=_("Concert Medical Service"),
            description=_("Your contact is Lisa Example. Her Phone number is 012345678910"),
            type=service_type,
            location="Town Square Gardens",
            active=True,
        )

        assign_perm("event_management.change_event", planners)
        assign_perm("event_management.view_event", planners)
        assign_perm("event_management.view_event", volunteers)

        Shift.objects.create(
            event=event,
            meeting_time=make_aware(datetime(2023, 6, 30, 15, 30)),
            start_time=make_aware(datetime(2023, 6, 30, 16, 0)),
            end_time=make_aware(datetime(2023, 7, 1, 1, 0)),
            signup_method_slug="instant_confirmation",
            signup_configuration=json.dumps(
                dict(minimum_age=18, signup_until=make_aware(datetime(2023, 6, 29, 8, 0)),),
                cls=DjangoJSONEncoder,
            ),
        )


class Command(BaseCommand):
    help = "Load initial data from datasets."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.datasets = {ds.identifier: ds(self) for ds in AVAILABLE_DATASET_CLASSES}

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(
            title="choosing the dataset",
            metavar="DATASET_IDENTIFIER",
            dest="dataset_identifier",
            help="Which data set to load. Available choices are:",
            required=True,
        )
        for dataset in self.datasets.values():
            dataset_parser = subparsers.add_parser(dataset.identifier, help=dataset.description)
            dataset.add_arguments(dataset_parser)

    def handle(self, *args, **options):
        if UserProfile.objects.exists():
            self.stdout.write("WARNING! User objects already exist in your database.")
            if input("Are you sure you want to continue? (yes/no) ") != "yes":
                self.stdout.write("Aborting...")
                return

        identifier = options["dataset_identifier"]
        with transaction.atomic():
            self.datasets[identifier].create_objects(*args, **options)
        self.stdout.write(self.style.SUCCESS("Done."))
