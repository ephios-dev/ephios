import urllib
from urllib.error import URLError

import pytest
from django.urls import reverse
from dynamic_preferences.registries import global_preferences_registry

from ephios.core.models import Qualification
from ephios.core.services.qualification import collect_all_included_qualifications
from ephios.plugins.qualification_management.importing import (
    RepoError,
    fetch_deserialized_qualifications_from_repo,
)
from tests.plugins.qualification_management.conftest import NOTSAN_UUID, SANH_UUID

try:
    with urllib.request.urlopen(
        "https://github.com/ephios-dev/ephios-qualification-fixtures/tree/main/test"
    ) as request:
        pass
except URLError:
    pytest.skip(
        "could not connect to github, so the importing tests are skipped", allow_module_level=True
    )


def test_repo_fetch():
    preferences = global_preferences_registry.manager()
    preferences["general__qualification_management_repos"] = (
        "https://github.com/ephios-dev/ephios-qualification-fixtures/raw/main/test/test.json"
    )
    assert list(fetch_deserialized_qualifications_from_repo())


def test_not_a_list_repo():
    preferences = global_preferences_registry.manager()
    preferences["general__qualification_management_repos"] = (
        "https://github.com/ephios-dev/ephios-qualification-fixtures/raw/main/test/not-a-list.json"
    )
    with pytest.raises(RepoError):
        list(fetch_deserialized_qualifications_from_repo())


def test_missing_key_repo():
    preferences = global_preferences_registry.manager()
    preferences["general__qualification_management_repos"] = (
        "https://github.com/ephios-dev/ephios-qualification-fixtures/raw/main/test/key-missing.json"
    )
    with pytest.raises(RepoError):
        list(fetch_deserialized_qualifications_from_repo())


def test_import_view(django_app, superuser):
    preferences = global_preferences_registry.manager()
    preferences["general__qualification_management_repos"] = (
        "https://github.com/ephios-dev/ephios-qualification-fixtures/raw/main/test/test.json"
    )
    form = django_app.get(
        reverse("qualification_management:settings_qualification_import"),
        user=superuser,
        status=200,
    ).form
    form[SANH_UUID] = True
    form[NOTSAN_UUID] = True
    assert not Qualification.objects.exists()
    form.submit().follow()
    assert Qualification.objects.count() == 2
    assert not Qualification.objects.exclude(uuid__in=[SANH_UUID, NOTSAN_UUID]).exists()
    assert set(
        collect_all_included_qualifications([Qualification.objects.get(uuid=NOTSAN_UUID)])
    ) == set(Qualification.objects.all())


def test_import_view_with_broken_repo(django_app, superuser):
    preferences = global_preferences_registry.manager()
    preferences["general__qualification_management_repos"] = (
        "https://github.com/ephios-dev/ephios-qualification-fixtures/raw/main/test/key-missing.json"
    )
    request = django_app.get(
        reverse("qualification_management:settings_qualification_import"),
        user=superuser,
        status=302,
    ).follow()
    assert "There was an error fetching one of the qualification repos" in request
