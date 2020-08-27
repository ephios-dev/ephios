from django.urls import path

from user_management import views

app_name = "user_management"
urlpatterns = [
    path("profile", views.ProfileView.as_view(), name="profile"),
]
