import uuid
from datetime import datetime

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import make_aware
from django.utils.translation import gettext as _
from guardian.shortcuts import assign_perm

from ephios.core.models import (
    Event,
    EventType,
    Qualification,
    QualificationCategory,
    Shift,
    UserProfile,
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
        assign_perm("core.add_event", planners)
        assign_perm("core.delete_event", planners)
        assign_perm("core.view_past_event", planners)
        assign_perm("core.view_userprofile", managers)
        assign_perm("core.add_userprofile", managers)
        assign_perm("core.change_userprofile", managers)
        assign_perm("core.delete_userprofile", managers)
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
            meeting_time=make_aware(datetime(2023, 6, 30, 15, 30)),
            start_time=make_aware(datetime(2023, 6, 30, 16, 0)),
            end_time=make_aware(datetime(2023, 7, 1, 1, 0)),
            signup_method_slug="instant_confirmation",
            signup_configuration=dict(
                minimum_age=18,
                signup_until=make_aware(datetime(2023, 6, 29, 8, 0)),
            ),
        )


@register_dataset
class DLRGQualificationDataset(AbstractDataset):
    identifier = "qualifications_dlrg"
    action = "Create qualification objects for water rescue and diving"

    def create_objects(self, *args, **options):
        # pylint: disable=too-many-locals,unused-variable,too-many-statements
        diving_category = QualificationCategory.objects.create(
            title=_("Diving"),
            uuid=uuid.UUID("6212a425-5cdf-49b0-bcb2-5075862a0c4a"),
        )

        signal = Qualification.objects.create(
            category=diving_category,
            title="Signalmann",
            abbreviation="Signalmann",
            uuid=uuid.UUID("436aaab0-5e8f-43aa-8f33-7d9ea68f7973"),
        )

        taucher_1 = Qualification.objects.create(
            category=diving_category,
            title="Einsatztaucher Stufe 1",
            abbreviation="ET1",
            uuid=uuid.UUID("52fc6a88-6e56-4af5-8021-b8a6412f405c"),
        )
        taucher_1.includes.add(signal)

        taucher_2 = Qualification.objects.create(
            category=diving_category,
            title="Einsatztaucher Stufe 2",
            abbreviation="ET2",
            uuid=uuid.UUID("481fc9fb-e90a-4b83-8a07-456034aa0a33"),
        )
        taucher_2.includes.add(taucher_1)

        tauchf = Qualification.objects.create(
            category=diving_category,
            title="Taucheinsatzführer",
            abbreviation="TEF",
            uuid=uuid.UUID("a3c5a3a0-f577-4bf5-8b2f-84108022d793"),
        )
        tauchf.includes.add(taucher_2)

        boats_category = QualificationCategory.objects.create(
            title=_("Boats (DLRG)"),
            uuid=uuid.UUID("f1e2619b-56ee-4e4a-b429-b923f8586771"),
        )
        Qualification.objects.create(
            category=boats_category,
            title="DLRG-Bootsführerschein A",
            abbreviation="BF Binnen",
            uuid=uuid.UUID("7ec0c9e2-f211-4370-b796-e309f3e9b448"),
        )
        Qualification.objects.create(
            category=boats_category,
            title="DLRG-Bootsführerschein B",
            abbreviation="BF See",
            uuid=uuid.UUID("1ba25ee1-fa88-4d44-9416-3a024caa6daf"),
        )

        drsa_category = QualificationCategory.objects.create(
            title=_("DRSA"),
            uuid=uuid.UUID("cd10e68f-41fe-4ca0-a624-3ab3eb85bd08"),
        )
        rettschw_bronze = Qualification.objects.create(
            category=drsa_category,
            title="Rettungsschwimmer Bronze",
            abbreviation="RS Bronze",
            uuid=uuid.UUID("247fab6a-8784-4976-a406-985fe47dc683"),
        )
        rettschw_silber = Qualification.objects.create(
            category=drsa_category,
            title="Rettungsschwimmer Silber",
            abbreviation="RS Silber",
            uuid=uuid.UUID("ef95a854-2eeb-431c-a795-bc291b341d49"),
        )
        rettschw_silber.includes.add(rettschw_bronze)
        rettschw_gold = Qualification.objects.create(
            category=drsa_category,
            title="Rettungsschwimmer Gold",
            abbreviation="RS Gold",
            uuid=uuid.UUID("b601a18b-cee8-4037-af33-dd7aabeac295"),
        )
        rettschw_gold.includes.add(rettschw_silber)

        wr_category = QualificationCategory.objects.create(
            title=_("Water rescue (DLRG)"),
            uuid=uuid.UUID("93574a61-1a6e-4dd5-8df3-40e8c51b693f"),
        )
        wr = Qualification.objects.create(
            category=wr_category,
            title="Fachausbildung Wasserrettungsdienst (DLRG)",
            abbreviation="FA WRD",
            uuid=uuid.UUID("bd7ca398-ed2a-4e97-b681-bc8fb1138ada"),
        )
        sr1 = Qualification.objects.create(
            category=wr_category,
            title="Strömungsretter I (DLRG)",
            abbreviation="Strömungsretter I",
            uuid=uuid.UUID("e1c1fac1-146d-4a52-935e-36455bcf0f87"),
        )
        sr1.includes.add(wr)
        sr2 = Qualification.objects.create(
            category=wr_category,
            title="Strömungsretter II (DLRG)",
            abbreviation="Strömungsretter II",
            uuid=uuid.UUID("9c506e7e-a456-4f22-8027-5365ab7dc58c"),
        )
        sr2.includes.add(sr1)

        radio_category = QualificationCategory.objects.create(
            title=_("Radio"),
            uuid=uuid.UUID("368fb612-f8c5-476a-a4e7-1478996a8ab3"),
        )
        Qualification.objects.create(
            category=radio_category,
            title="BOS-Sprechfunker -digital-",
            abbreviation="Digitalfunk",
            uuid=uuid.UUID("506c4d4c-df11-4d41-95d7-c4ddfc78b706"),
        )
        Qualification.objects.create(
            category=radio_category,
            title="BOS-Sprechfunker -analog-",
            abbreviation="Analogfunk",
            uuid=uuid.UUID("4974ea66-2086-4987-958b-503de21a285a"),
        )
        Qualification.objects.create(
            category=radio_category,
            title="DLRG-Sprechfunker",
            abbreviation="DLRG-Sprechfunker",
            uuid=uuid.UUID("e8ff96da-0dd3-4664-9b9d-3c4abc1f40de"),
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
