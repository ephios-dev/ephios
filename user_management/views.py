from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.urls import reverse
from django.views.generic import DetailView, ListView, UpdateView, CreateView, DeleteView
from guardian.shortcuts import get_users_with_perms, get_objects_for_group

from user_management.forms import GroupForm
from django.utils.translation import gettext as _

from user_management.models import UserProfile


class ProfileView(LoginRequiredMixin, DetailView):
    def get_object(self, queryset=None):
        return self.request.user


class UserProfileListView(PermissionRequiredMixin, ListView):
    model = UserProfile
    permission_required = "user.view_user"

    def get_queryset(self):
        return UserProfile.objects.all()


class GroupListView(PermissionRequiredMixin, ListView):
    model = Group
    permission_required = "auth.view_group"
    template_name = "user_management/group_list.html"


class GroupCreateView(PermissionRequiredMixin, CreateView):
    model = Group
    permission_required = "auth.add_group"
    template_name = "user_management/group_form.html"
    form_class = GroupForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["initial"] = {
            "users": UserProfile.objects.none(),
            "can_add_event": False,
            "publish_event_for_group": Group.objects.none(),
        }
        return kwargs

    def get_success_url(self):
        messages.success(self.request, _("Group successfully created."))
        return reverse("user_management:group_list")


class GroupUpdateView(PermissionRequiredMixin, UpdateView):
    model = Group
    permission_required = "auth.change_group"
    template_name = "user_management/group_form.html"
    form_class = GroupForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["initial"] = {
            "users": self.object.user_set.all(),
            "can_add_event": self.object.permissions.filter(codename="add_event").exists(),
            "publish_event_for_group": get_objects_for_group(
                self.object, "publish_event_for_group", klass=Group
            ),
        }
        return kwargs

    def get_success_url(self):
        return reverse("user_management:group_list")


class GroupDeleteView(PermissionRequiredMixin, DeleteView):
    model = Group
    permission_required = "auth.delete_group"
    template_name = "user_management/group_confirm_delete.html"

    def get_success_url(self):
        return reverse("user_management:group_list")
