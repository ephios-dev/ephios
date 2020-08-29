from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import DetailView, ListView, CreateView

from user_management.models import UserProfile


class ProfileView(LoginRequiredMixin, DetailView):
    def get_object(self, queryset=None):
        return self.request.user


class UserProfileListView(PermissionRequiredMixin, ListView):
    model = UserProfile
    permission_required = "user.view_user"

    def get_queryset(self):
        return UserProfile.objects.all()


class UserProfileCreateView(PermissionRequiredMixin, CreateView):
    template_name = "user_management/userprofile_form.html"
    permission_required = "user_management.add_user"
    queryset = UserProfile.objects.all()
    fields = ["email", "first_name", "last_name", "date_of_birth", "phone"]

    def get_success_url(self):
        return reverse("user_management:user_list")
