import pytest
from django.core.management import call_command

from ephios.core.models import Qualification


@pytest.mark.django_db
def test_qualifications(django_app):
    call_command("setupdata", "qualifications")
    assert Qualification.objects.get(title="Ersthelfer")


@pytest.mark.django_db
def test_qualifications(django_app):
    call_command("setupdata", "qualifications_dlrg")
    assert Qualification.objects.get(title="Rettungsschwimmer Silber")
