import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestUserProfileView:
    def test_no_permission_required(self, django_app, volunteer):
        response = django_app.get(reverse("user_management:profile"), user=volunteer)
        assert response.status_code == 200
