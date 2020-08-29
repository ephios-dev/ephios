from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import render
from django.views.generic import DetailView, ListView

from user_management.models import UserProfile


class ProfileView(LoginRequiredMixin, DetailView):
    def get_object(self, queryset=None):
        return self.request.user


class UserProfileListView(PermissionRequiredMixin, ListView):
    model = UserProfile
    permission_required = "user.view_user"

    def get_queryset(self):
        return UserProfile.objects.all()
