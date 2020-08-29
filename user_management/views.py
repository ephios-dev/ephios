from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import render
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

    def get_form(self, form_class=None):
        pass

    def get_context_data(self, **kwargs):
        pass

    def get_success_url(self):
        pass
