from django.core.management import call_command

from ephios.core.models import UserProfile


def test_devdata(django_app):
    call_command("devdata")
    assert UserProfile.objects.get(email="admin@localhost")
