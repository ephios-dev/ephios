from datetime import datetime

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from guardian.shortcuts import assign_perm

from django.utils.translation import gettext as _

from user_management.models import UserProfile

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
    action = "Create a planner and volunteers group and add the superuser to it."

    def create_objects(self, *args, **options):
        super().create_objects(*args, **options)
        from django.contrib.auth.models import Group

        volunteers = Group.objects.create(name=_("Volunteers"))
        volunteers.user_set.add(self.admin_user)
        volunteers.save()

        planners = Group.objects.create(name=_("Planners"))
        planners.user_set.add(self.admin_user)
        planners.save()

        assign_perm("publish_event_for_group", planners, volunteers)
        assign_perm("event_management.add_event", planners)
        assign_perm("event_management.delete_event", planners)


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
        self.datasets[identifier].create_objects(*args, **options)
        self.stdout.write(self.style.SUCCESS("Done."))
