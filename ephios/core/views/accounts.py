from django.contrib import messages
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Prefetch
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)
from django.views.generic.detail import SingleObjectMixin
from dynamic_preferences.registries import global_preferences_registry

from ephios.core.forms.users import (
    GroupForm,
    QualificationGrantFormset,
    UserNotificationPreferenceForm,
    UserProfileForm,
)
from ephios.core.models import QualificationGrant, UserProfile
from ephios.core.services.notifications.types import (
    NewProfileNotification,
    ProfileUpdateNotification,
)
from ephios.extra.mixins import CustomPermissionRequiredMixin


class ProfileView(LoginRequiredMixin, DetailView):
    def get_object(self, queryset=None):
        return self.request.user


class UserProfileListView(CustomPermissionRequiredMixin, ListView):
    model = UserProfile
    permission_required = "core.view_userprofile"
    ordering = "last_name"

    def get_queryset(self):
        global_preferences = global_preferences_registry.manager()
        categories = global_preferences["general__relevant_qualification_categories"]
        qs = UserProfile.objects.all()
        for category in categories:
            qs = qs.prefetch_related(
                Prefetch(
                    "qualification_grants",
                    queryset=QualificationGrant.objects.filter(
                        qualification__category=category,
                    ).select_related("qualification"),
                    to_attr=f"qualifications_for_category_{category.pk}",
                )
            )
        return qs.order_by("last_name", "first_name")


class UserProfileCreateView(CustomPermissionRequiredMixin, TemplateView):
    template_name = "core/userprofile_form.html"
    permission_required = "core.add_userprofile"
    model = UserProfile

    def get_context_data(self, **kwargs):
        kwargs.setdefault(
            "userprofile_form", UserProfileForm(self.request.POST or None, request=self.request)
        )
        kwargs.setdefault(
            "qualification_formset", QualificationGrantFormset(self.request.POST or None)
        )
        return super().get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        userprofile_form = UserProfileForm(self.request.POST, request=request)
        qualification_formset = QualificationGrantFormset(self.request.POST)
        if all((userprofile_form.is_valid(), qualification_formset.is_valid())):
            userprofile = userprofile_form.save()
            qualification_formset.instance = userprofile
            qualification_formset.save()
            messages.success(
                self.request,
                _("User {name} ({email}) added successfully.").format(
                    name=userprofile.get_full_name(), email=userprofile.email
                ),
            )
            if userprofile.is_active:
                NewProfileNotification.send(userprofile)
            return redirect(reverse("core:userprofile_list"))
        return self.render_to_response(
            self.get_context_data(
                userprofile_form=userprofile_form, qualification_formset=qualification_formset
            )
        )


class UserProfileUpdateView(CustomPermissionRequiredMixin, SingleObjectMixin, TemplateView):
    model = UserProfile
    permission_required = "core.change_userprofile"
    template_name = "core/userprofile_form.html"

    def get_userprofile_form(self):
        return UserProfileForm(
            self.request.POST or None,
            initial={
                "groups": self.get_object().groups.all(),
            },
            instance=self.object,
            request=self.request,
        )

    def get_qualification_formset(self):
        return QualificationGrantFormset(self.request.POST or None, instance=self.object)

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        kwargs.setdefault("userprofile_form", self.get_userprofile_form())
        kwargs.setdefault("qualification_formset", self.get_qualification_formset())
        return super().get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        userprofile_form = self.get_userprofile_form()
        qualification_formset = self.get_qualification_formset()
        if all((userprofile_form.is_valid(), qualification_formset.is_valid())):
            userprofile = userprofile_form.save()
            qualification_formset.save()
            messages.success(
                self.request,
                _("User {name} ({user}) updated successfully.").format(
                    name=self.object.get_full_name(), user=self.object
                ),
            )
            ProfileUpdateNotification.send(userprofile)
            return redirect(reverse("core:userprofile_list"))

        return self.render_to_response(
            self.get_context_data(
                userprofile_form=userprofile_form, qualification_formset=qualification_formset
            )
        )


class UserProfileDeleteView(CustomPermissionRequiredMixin, DeleteView):
    model = UserProfile
    permission_required = "core.delete_userprofile"
    template_name = "core/userprofile_confirm_delete.html"

    def get_success_url(self):
        messages.info(
            self.request,
            _("The user {name} ({user}) was deleted.").format(
                name=self.object.get_full_name(), user=self.object
            ),
        )
        return reverse("core:userprofile_list")


class UserProfilePasswordResetView(CustomPermissionRequiredMixin, SingleObjectMixin, TemplateView):
    model = UserProfile
    permission_required = "core.change_userprofile"
    template_name = "core/userprofile_confirm_password_reset.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.object = self.get_object()

    def post(self, request, *args, **kwargs):
        if request.POST.get("confirm"):
            form = PasswordResetForm(
                {
                    "email": self.object.email,
                }
            )
            if form.is_valid():
                form.save(request=request)
                messages.info(
                    request,
                    _(
                        "The user's password has been reset. An email was sent to {email}.".format(
                            email=self.object.email
                        )
                    ),
                )
            else:
                messages.error(
                    request,
                    _(
                        "No valid email address ({email}). The password has not been reset.".format(
                            email=self.object.email
                        )
                    ),
                )
            return redirect(reverse("core:userprofile_list"))
        return self.render_to_response({"userprofile": self.object})


class UserProfileNotificationsView(LoginRequiredMixin, SuccessMessageMixin, FormView):
    template_name = "core/userprofile_notifications.html"
    success_message = _("Settings succesfully saved.")

    def get_form(self, form_class=None):
        return UserNotificationPreferenceForm(self.request.POST or None, user=self.request.user)

    def get_success_url(self):
        return reverse("core:profile_notifications")

    def form_valid(self, form):
        form.update_preferences()
        return super().form_valid(form)


class GroupListView(CustomPermissionRequiredMixin, ListView):
    model = Group
    permission_required = "auth.view_group"
    template_name = "core/group_list.html"
    ordering = "name"


class GroupCreateView(CustomPermissionRequiredMixin, CreateView):
    model = Group
    permission_required = "auth.add_group"
    accept_object_perms = False
    template_name = "core/group_form.html"
    form_class = GroupForm

    def get_success_url(self):
        messages.success(
            self.request, _('Group "{group}" created successfully.').format(group=self.object)
        )
        return reverse("core:group_list")


class GroupUpdateView(CustomPermissionRequiredMixin, UpdateView):
    model = Group
    permission_required = "auth.change_group"
    template_name = "core/group_form.html"
    form_class = GroupForm

    def get_success_url(self):
        messages.success(
            self.request, _('Group "{group}" updated successfully.').format(group=self.object)
        )
        return reverse("core:group_list")


class GroupDeleteView(CustomPermissionRequiredMixin, DeleteView):
    model = Group
    permission_required = "auth.delete_group"
    template_name = "core/group_confirm_delete.html"

    def get_success_url(self):
        messages.info(self.request, _('The group "{group}" was deleted.').format(group=self.object))
        return reverse("core:group_list")
