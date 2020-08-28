from django.urls import path

from user_management import views

app_name = "user_management"
urlpatterns = [
    path("users/", views.UserProfileListView.as_view(), name="user_list",),
]
