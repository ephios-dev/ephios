import pytest
from django.test import override_settings
from django.urls import reverse


@pytest.mark.django_db
class TestSettings:
    @override_settings(COMPRESS_ENABLED=True)
    def test_compression(self, django_app, volunteer):
        response = django_app.get(reverse("event_management:index"), user=volunteer)
        response.showbrowser()
        assert response.status_code == 200
