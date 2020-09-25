from django.urls import path

from ephios.user_management import views

app_name = "user_management"
urlpatterns = [
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("groups/", views.GroupListView.as_view(), name="group_list"),
    path("groups/<int:pk>/edit", views.GroupUpdateView.as_view(), name="group_edit"),
    path("groups/<int:pk>/delete", views.GroupDeleteView.as_view(), name="group_delete"),
    path("groups/create", views.GroupCreateView.as_view(), name="group_add"),
    path(
        "users/",
        views.UserProfileListView.as_view(),
        name="userprofile_list",
    ),
    path(
        "users/<int:pk>/edit",
        views.UserProfileUpdateView.as_view(),
        name="userprofile_edit",
    ),
    path(
        "users/<int:pk>/delete",
        views.UserProfileDeleteView.as_view(),
        name="userprofile_delete",
    ),
    path(
        "users/create/",
        views.UserProfileCreateView.as_view(),
        name="userprofile_create",
    ),
]
