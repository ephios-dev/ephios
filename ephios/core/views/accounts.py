from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import Group
from django.db.models import Q, QuerySet
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView
from django.views.generic.detail import SingleObjectMixin
from django_select2.forms import Select2MultipleWidget

from ephios.api.access.auth import revoke_all_access_tokens
from ephios.core.forms.users import (
    DeleteGroupForm,
    DeleteUserProfileForm,
    GroupForm,
    QualificationGrantFormset,
    UserProfileForm,
)
from ephios.core.models import UserProfile
from ephios.core.services.notifications.types import (
    NewProfileNotification,
    ProfileUpdateNotification,
)
from ephios.extra.mixins import CustomPermissionRequiredMixin


class UserProfileFilterForm(forms.Form):
    query = forms.CharField(
        label=_("Search for…"),
        widget=forms.TextInput(attrs={"placeholder": _("Search for…"), "autofocus": "autofocus"}),
        required=False,
    )
    groups = forms.ModelMultipleChoiceField(
        label=_("groups"),
        # help_text=_("Only show users that are in any of these groups."),
        queryset=Group.objects.all(),
        required=False,
        widget=Select2MultipleWidget(
            attrs={
                "data-placeholder": _("restrict to groups"),
                "classes": "w-auto",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)

    def filter(self, qs: QuerySet[UserProfile]):
        fdata = self.cleaned_data

        if groups := fdata.get("groups"):
            qs = qs.filter(groups__in=groups)

        if query := fdata.get("query"):
            qs = qs.filter(
                Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(email__icontains=query)
            )
        return qs.distinct()


class UserProfileListView(CustomPermissionRequiredMixin, ListView):
    model = UserProfile
    permission_required = "core.view_userprofile"
    paginate_by = settings.DEFAULT_LISTVIEW_PAGINATION

    @cached_property
    def filter_form(self):
        return UserProfileFilterForm(data=self.request.GET or None, request=self.request)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter_form"] = self.filter_form
        return ctx

    def get_queryset(self):
        qs = UserProfile.objects.all().prefetch_related("groups").prefetch_show_grants()
        if self.filter_form.is_valid():
            qs = self.filter_form.filter(qs)
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
                _("User {name} ({email}) updated successfully.").format(
                    name=self.object.get_full_name(), email=self.object.email
                ),
            )
            if request.user != userprofile:
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
    form_class = DeleteUserProfileForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.object
        return kwargs

    def get_success_url(self):
        messages.info(
            self.request,
            _("The user {name} ({email}) was deleted.").format(
                name=self.object.get_full_name(), email=self.object.email
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
                    _("The user's password has been reset. An email was sent to {email}.").format(
                        email=self.object.email
                    ),
                )
            else:
                messages.error(
                    request,
                    _("No valid email address ({email}). The password has not been reset.").format(
                        email=self.object.email
                    ),
                )
        return redirect(reverse("core:userprofile_list"))


class UserProfilePasswordTokenRevokationView(
    CustomPermissionRequiredMixin, SingleObjectMixin, TemplateView
):
    model = UserProfile
    permission_required = "core.change_userprofile"
    template_name = "core/userprofile_confirm_password_token_revokation.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.object: UserProfile = self.get_object()

    def post(self, request, *args, **kwargs):
        if request.POST.get("confirm"):
            self.object.set_unusable_password()
            self.object.save()
            revoke_all_access_tokens(self.object)
            messages.info(request, _("The user's password and API tokens have been revoked."))
        return redirect(reverse("core:userprofile_list"))


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
    form_class = DeleteGroupForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.object
        return kwargs

    def get_success_url(self):
        messages.info(self.request, _('The group "{group}" was deleted.').format(group=self.object))
        return reverse("core:group_list")
