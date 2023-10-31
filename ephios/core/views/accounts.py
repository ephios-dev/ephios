from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import Group, Permission
from django.db.models import Count, Exists, OuterRef, Prefetch, Q, QuerySet
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView
from django.views.generic.detail import SingleObjectMixin
from django_select2.forms import ModelSelect2Widget, Select2Widget

from ephios.api.access.auth import revoke_all_access_tokens
from ephios.core.forms.users import (
    HR_TEST_PERMISSION,
    MANAGEMENT_TEST_PERMISSION,
    PLANNING_TEST_PERMISSION,
    DeleteGroupForm,
    DeleteUserProfileForm,
    GroupForm,
    QualificationGrantFormset,
    UserProfileForm,
)
from ephios.core.models import Qualification, QualificationGrant, UserProfile
from ephios.core.models.users import IdentityProvider
from ephios.core.services.notifications.types import (
    NewProfileNotification,
    ProfileUpdateNotification,
)
from ephios.core.services.qualification import uuids_of_qualifications_fulfilling_any_of
from ephios.extra.mixins import CustomPermissionRequiredMixin


class UserProfileFilterForm(forms.Form):
    query = forms.CharField(
        label=_("Search for…"),
        widget=forms.TextInput(attrs={"placeholder": _("Search for…"), "autofocus": "autofocus"}),
        required=False,
    )
    group = forms.ModelChoiceField(
        label=_("Group"),
        queryset=Group.objects.all(),
        required=False,
        widget=Select2Widget(
            attrs={
                "data-placeholder": _("Group membership"),
                "classes": "w-auto",
            }
        ),
    )
    qualification = forms.ModelChoiceField(
        label=_("Qualification"),
        queryset=Qualification.objects.all(),
        required=False,
        widget=ModelSelect2Widget(
            search_fields=["title__icontains", "abbreviation__icontains"],
            attrs={
                "data-placeholder": _("Qualification"),
                "classes": "w-auto",
            },
        ),
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)

    def filter(self, qs: QuerySet[UserProfile]):
        fdata = self.cleaned_data

        if query := fdata.get("query"):
            qs = qs.filter(Q(display_name__icontains=query) | Q(email__icontains=query))

        if group := fdata.get("group"):
            qs = qs.filter(groups=group)

        if qualification := fdata.get("qualification"):
            qs = qs.filter(
                qualification_grants__in=QualificationGrant.objects.unexpired().filter(
                    qualification__uuid__in=uuids_of_qualifications_fulfilling_any_of(
                        [qualification]
                    )
                )
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
        qs = UserProfile.objects.all().prefetch_related(
            "groups",
            Prefetch(
                "qualification_grants",
                queryset=QualificationGrant.objects.select_related(
                    "qualification", "qualification__category"
                ),
            ),
        )
        if self.filter_form.is_valid():
            qs = self.filter_form.filter(qs)
        return qs.order_by("display_name")


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
        kwargs.setdefault(
            "oidc_group_claims", IdentityProvider.objects.filter(group_claim__isnull=False).exists()
        )
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

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .prefetch_related(
                "user_set",
            )
            .annotate(
                user_count=Count("user"),
                **{
                    attr: Exists(
                        Permission.objects.filter(
                            codename=codename,
                            group=OuterRef("pk"),
                            content_type__app_label=app_label,
                        )
                    )
                    for attr, app_label, codename in [
                        ("is_planning_group", *PLANNING_TEST_PERMISSION.split(".")),
                        ("is_hr_group", *HR_TEST_PERMISSION.split(".")),
                        ("is_management_group", *MANAGEMENT_TEST_PERMISSION.split(".")),
                    ]
                },
            )
        )


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

    def get_context_data(self, **kwargs):
        kwargs.setdefault(
            "oidc_group_claims", IdentityProvider.objects.filter(group_claim__isnull=False).exists()
        )
        return super().get_context_data(**kwargs)

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
