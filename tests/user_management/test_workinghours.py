import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestWorkingHours:
    def test_profile_without_hours(self, django_app, volunteer):
        response = django_app.get(reverse("user_management:profile"), user=volunteer)
        assert response.status_code == 200
        assert response.html.find(text="0.0 hours")

    def test_profile_with_hours(self, django_app, volunteer, workinghours):
        response = django_app.get(reverse("user_management:profile"), user=volunteer)
        assert response.html.find(text=workinghours[0].reason)
        assert response.html.find(text=workinghours[1].reason)
        total_hours = workinghours[0].hours + workinghours[1].hours
        assert response.html.find(text=f"{total_hours:.1f} hours")
