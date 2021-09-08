from urllib.error import HTTPError

import pytest

from ephios.plugins.qualification_management.importing import (
    fetch_deserialized_qualifications_from_repo,
)


def test_repo_fetch():
    try:
        # this test is slow, as it connects to the internet
        assert list(fetch_deserialized_qualifications_from_repo())
    except HTTPError:
        pytest.skip("Downloading the qualification repo failed")
