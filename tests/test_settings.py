from django.test import override_settings
from django.urls import reverse


class TestSettings:
    @override_settings(COMPRESS_ENABLED=True)
    def test_compression(self, django_app, volunteer):
        response = django_app.get(reverse("core:home"), user=volunteer)
        assert response.status_code == 200
