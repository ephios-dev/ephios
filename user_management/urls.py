from django.urls import path

from user_management import views

app_name = "user_management"
urlpatterns = [
    path("profile/", views.ProfileView.as_view(), name="profile",),
    path("users/", views.UserProfileListView.as_view(), name="user_list",),
    path("users/create/", views.UserProfileCreateView.as_view(), name="userprofile_create",),
]
