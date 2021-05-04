from django.core.management import call_command

from ephios.core.models import Qualification


def test_qualifications(django_app):
    call_command("setupdata", "qualifications")
    assert Qualification.objects.get(title="Ersthelfer")


def test_qualifications_dlrg(django_app):
    call_command("setupdata", "qualifications_dlrg")
    assert Qualification.objects.get(title="Rettungsschwimmer Silber")
