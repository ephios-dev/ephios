import uuid
from urllib.error import URLError

import pytest
from django.urls import reverse

from ephios.core.models import Qualification
from ephios.plugins.qualification_management.importing import (
    fetch_deserialized_qualifications_from_repo,
)


def test_repo_fetch():
    try:
        # this test is slow, as it connects to the internet
        assert list(fetch_deserialized_qualifications_from_repo())
    except URLError:
        pytest.skip("Downloading the qualification repo failed")


RETTSAN_UUID = "0b41fac6-ca9e-4b8a-82c5-849412187351"


def test_import_view(django_app, superuser, groups):
    form = django_app.get(
        reverse("qualification_management:settings_qualification_import"),
        user=superuser,
        status=200,
    ).form
    form[RETTSAN_UUID] = True
    assert not Qualification.objects.exists()
    form.submit()
    assert Qualification.objects.get().uuid == uuid.UUID(RETTSAN_UUID)
