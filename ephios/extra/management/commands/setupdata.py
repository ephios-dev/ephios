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
class QualificationDataset(AbstractDataset):
    identifier = "qualifications"
    action = "Create qualification objects for medical qualifications and driver licenses"

    def create_objects(self, *args, **options):
        # pylint: disable=too-many-locals,unused-variable,too-many-statements
        medical_category = QualificationCategory.objects.create(
            title=_("Medical"),
            uuid=uuid.UUID("50380292-b9c9-4711-b70d-8e03e2784cfb"),
        )

        eh = Qualification.objects.create(
            category=medical_category,
            title="Ersthelfer",
            abbreviation="EH",
            uuid=uuid.UUID("8bdb343e-d78d-4cc9-80e7-7ccc36b556e1"),
        )

        sana = Qualification.objects.create(
            category=medical_category,
            title="Sanitäter A",
            abbreviation="San A",
            uuid=uuid.UUID("cdb595e8-1dcb-46d2-8013-b915f818b321"),
        )
        sana.included_qualifications.add(eh)

        sanb = Qualification.objects.create(
            category=medical_category,
            title="Sanitäter B",
            abbreviation="San B",
            uuid=uuid.UUID("3fc86c78-2b87-49f7-8721-af7f8d51747c"),
        )
        sanb.included_qualifications.add(sana)

        sanh = Qualification.objects.create(
            category=medical_category,
            title="Sanitätshelfer",
            abbreviation="SanH",
            uuid=uuid.UUID("b1faab38-2e7c-4507-b753-06d1e653412d"),
        )
        sanh.included_qualifications.add(eh)
        sanh.included_qualifications.add(sanb)

        rh = Qualification.objects.create(
            category=medical_category,
            title="Rettungshelfer",
            abbreviation="RH",
            uuid=uuid.UUID("de6c2449-a764-4c39-8f44-de276e99451b"),
        )
        rh.included_qualifications.add(sanh)

        rs = Qualification.objects.create(
            category=medical_category,
            title="Rettungssanitäter",
            abbreviation="RettSan",
            uuid=uuid.UUID("0b41fac6-ca9e-4b8a-82c5-849412187351"),
        )
        rs.included_qualifications.add(rh)

        ra = Qualification.objects.create(
            category=medical_category,
            title="Rettungsassistent",
            abbreviation="RA",
            uuid=uuid.UUID("2a24e395-fa02-4b2e-8215-7763b04d85c8"),
        )
        ra.included_qualifications.add(rs)

        nfs = Qualification.objects.create(
            category=medical_category,
            title="Notfallsanitäter",
            abbreviation="NFS",
            uuid=uuid.UUID("d114125b-7cf4-49e2-8908-f93e2f95dfb8"),
        )
        nfs.included_qualifications.add(ra)

        na = Qualification.objects.create(
            category=medical_category,
            title="Notarzt",
            abbreviation="NA",
            uuid=uuid.UUID("cb4f4ebc-3adf-4d32-a427-0ac0f686038a"),
        )

        driverslicense_category = QualificationCategory.objects.create(
            title=_("License"),
            uuid=uuid.UUID("a5669cc2-7444-4046-8c33-d8ee0bbf881b"),
        )

        # noinspection PyPep8
        l = Qualification.objects.create(
            category=driverslicense_category,
            title="Fahrerlaubnis Klasse L",
            abbreviation="Fe L",
            uuid=uuid.UUID("1c007860-48eb-4c86-a35b-45c6de903de4"),
        )

        t = Qualification.objects.create(
            category=driverslicense_category,
            title="Fahrerlaubnis Klasse T",
            abbreviation="Fe T",
            uuid=uuid.UUID("cc5ab73d-a1d6-4e95-93d2-aaf6c51ae91f"),
        )

        am = Qualification.objects.create(
            category=driverslicense_category,
            title="Fahrerlaubnis Klasse AM",
            abbreviation="Fe AM",
            uuid=uuid.UUID("f96bdfef-f1b8-46aa-8755-e506075ebc88"),
        )

        a1 = Qualification.objects.create(
            category=driverslicense_category,
            title="Fahrerlaubnis Klasse A1",
            abbreviation="Fe A1",
            uuid=uuid.UUID("d7e9da8f-8386-4e7d-8706-62103bfe78f1"),
        )
        a1.included_qualifications.add(am)

        a2 = Qualification.objects.create(
            category=driverslicense_category,
            title="Fahrerlaubnis Klasse A2",
            abbreviation="Fe A2",
            uuid=uuid.UUID("fe06530c-8216-40a0-81dd-2beaa8d803e1"),
        )
        a2.included_qualifications.add(a1)

        a = Qualification.objects.create(
            category=driverslicense_category,
            title="Fahrerlaubnis Klasse A",
            abbreviation="Fe A",
            uuid=uuid.UUID("4ff00daa-1501-41c0-8d89-2e54cb43f293"),
        )
        a.included_qualifications.add(a2)

        b = Qualification.objects.create(
            category=driverslicense_category,
            title="Fahrerlaubnis Klasse B",
            abbreviation="Fe B",
            uuid=uuid.UUID("0715b687-877a-4fed-bde0-5ea06b1043fc"),
        )
        b.included_qualifications.add(am)
        b.included_qualifications.add(l)

        be = Qualification.objects.create(
            category=driverslicense_category,
            title="Fahrerlaubnis Klasse BE",
            abbreviation="Fe BE",
            uuid=uuid.UUID("31529f69-09d7-44cc-84f6-19fbfd949faa"),
        )
        be.included_qualifications.add(b)

        c1 = Qualification.objects.create(
            category=driverslicense_category,
            title="Fahrerlaubnis Klasse C1",
            abbreviation="Fe C1",
            uuid=uuid.UUID("c9898e6c-4ecf-4781-9c0a-884861e36a81"),
        )
        c1.included_qualifications.add(b)

        c = Qualification.objects.create(
            category=driverslicense_category,
            title="Fahrerlaubnis Klasse C",
            abbreviation="Fe C",
            uuid=uuid.UUID("2d2fc932-5206-4c2c-bb63-0bc579acea6f"),
        )
        c.included_qualifications.add(c1)

        c1e = Qualification.objects.create(
            category=driverslicense_category,
            title="Fahrerlaubnis Klasse C1E",
            abbreviation="Fe C1E",
            uuid=uuid.UUID("f5e3be89-59de-4b13-a92f-5949009f62d8"),
        )
        c1e.included_qualifications.add(c1)
        c1e.included_qualifications.add(be)

        ce = Qualification.objects.create(
            category=driverslicense_category,
            title="Fahrerlaubnis Klasse CE",
            abbreviation="Fe CE",
            uuid=uuid.UUID("736ca05a-7ff9-423a-9fa4-8b4641fde29c"),
        )
        ce.included_qualifications.add(c)
        ce.included_qualifications.add(c1e)

        d1 = Qualification.objects.create(
            category=driverslicense_category,
            title="Fahrerlaubnis Klasse D1",
            abbreviation="Fe D1",
            uuid=uuid.UUID("3df818c6-f4a7-400e-a5bf-64ed087f79ab"),
        )
        d1.included_qualifications.add(b)

        d = Qualification.objects.create(
            category=driverslicense_category,
            title="Fahrerlaubnis Klasse D",
            abbreviation="Fe D",
            uuid=uuid.UUID("3238a892-afa8-4e76-b9b9-87d8765c5b72"),
        )
        d.included_qualifications.add(d1)

        d1e = Qualification.objects.create(
            category=driverslicense_category,
            title="Fahrerlaubnis Klasse D1E",
            abbreviation="Fe D1E",
            uuid=uuid.UUID("5d0ab40e-fade-4d45-9882-0039118a2445"),
        )
        d1e.included_qualifications.add(d1)
        d1e.included_qualifications.add(be)

        de = Qualification.objects.create(
            category=driverslicense_category,
            title="Fahrerlaubnis Klasse DE",
            abbreviation="Fe DE",
            uuid=uuid.UUID("64495d88-3ec0-4bbe-bc2b-78b6e6cfbc25"),
        )
        de.included_qualifications.add(d)
        de.included_qualifications.add(d1e)


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
        taucher_1.included_qualifications.add(signal)

        taucher_2 = Qualification.objects.create(
            category=diving_category,
            title="Einsatztaucher Stufe 2",
            abbreviation="ET2",
            uuid=uuid.UUID("481fc9fb-e90a-4b83-8a07-456034aa0a33"),
        )
        taucher_2.included_qualifications.add(taucher_1)

        tauchf = Qualification.objects.create(
            category=diving_category,
            title="Taucheinsatzführer",
            abbreviation="TEF",
            uuid=uuid.UUID("a3c5a3a0-f577-4bf5-8b2f-84108022d793"),
        )
        tauchf.included_qualifications.add(taucher_2)

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
        rettschw_silber.included_qualifications.add(rettschw_bronze)
        rettschw_gold = Qualification.objects.create(
            category=drsa_category,
            title="Rettungsschwimmer Gold",
            abbreviation="RS Gold",
            uuid=uuid.UUID("b601a18b-cee8-4037-af33-dd7aabeac295"),
        )
        rettschw_gold.included_qualifications.add(rettschw_silber)

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
        sr1.included_qualifications.add(wr)
        sr2 = Qualification.objects.create(
            category=wr_category,
            title="Strömungsretter II (DLRG)",
            abbreviation="Strömungsretter II",
            uuid=uuid.UUID("9c506e7e-a456-4f22-8027-5365ab7dc58c"),
        )
        sr2.included_qualifications.add(sr1)

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
