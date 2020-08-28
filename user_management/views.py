from django.shortcuts import render
from django.views.generic import ListView

from user_management.models import UserProfile


class UserProfileListView(ListView):
    model = UserProfile

    def get_queryset(self):
        return UserProfile.objects.all()
