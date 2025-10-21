from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.db.models import Q, QuerySet
from django.http import (
    HttpResponseRedirect,
    HttpResponseForbidden,
)
from django.urls import reverse_lazy
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    ListView,
    FormView,
    DeleteView,
)
from django_select2.forms import ModelSelect2Widget

from ephios.core.models import Qualification, QualificationGrant
from ephios.extra.mixins import CustomPermissionRequiredMixin
from ephios.plugins.qualification_requests.forms import (
    QualificationRequestCreateForm,
    QualificationRequestCheckForm,
)
from ephios.plugins.qualification_requests.models import QualificationRequest

class UserProfileFilterForm(forms.Form):
    query = forms.CharField(
        label=_("Search for…"),
        widget=forms.TextInput(attrs={"placeholder": _("Search for…"), "autofocus": "autofocus"}),
        required=False,
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
    status = forms.ChoiceField(
        label=_("Status"),
        choices=[
            ("", _("Any status")),
            ("pending", _("Pending")),
            ("approved", _("Approved")),
            ("rejected", _("Rejected")),
        ],
        required=False,
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)

    def filter(self, qs: QuerySet[QualificationRequest]):
        fdata = self.cleaned_data

        if query := fdata.get("query"):
            qs = qs.filter(Q(user__display_name__icontains=query) | Q(user__email__icontains=query))

        if qualification := fdata.get("qualification"):
            qs = qs.filter(qualification=qualification)

        if status := fdata.get("status"):
            qs = qs.filter(status=status)

        return qs.distinct()

class QualificationRequestListView(CustomPermissionRequiredMixin, ListView):
    model = QualificationRequest
    ordering = ("-created_at")
    template_name = "qualification_requests/qualification_requests_list.html"
    permission_required = "core.view_userprofile"

    @cached_property
    def filter_form(self):
        return UserProfileFilterForm(data=self.request.GET or None, request=self.request)
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter_form"] = self.filter_form
        return ctx

    def get_queryset(self):
        qs = QualificationRequest.objects.select_related("user", "qualification")
        if self.filter_form.is_valid():
            qs = self.filter_form.filter(qs)
        return qs.order_by("-created_at", "-user__display_name")

class QualificationRequestOwnListView(LoginRequiredMixin, ListView):
    model = QualificationRequest
    ordering = ("-created_at",)
    template_name = "qualification_requests/qualification_requests_list_own.html"

    def get_queryset(self):
        return QualificationRequest.objects.filter(user=self.request.user).order_by("-created_at")

class QualificationRequestOwnCreateView(LoginRequiredMixin, FormView):
    model = QualificationRequest
    form_class = QualificationRequestCreateForm
    template_name = "qualification_requests/qualification_requests_add_form.html"
    success_url = reverse_lazy("qualification_requests:qualification_requests_list_own")

    def form_valid(self, form):
        QualificationRequest.objects.create(
            user=self.request.user,
            qualification=form.instance.qualification,
            qualification_date=form.instance.qualification_date,
            user_comment=form.instance.user_comment,
        )

        return super().form_valid(form)

class QualificationRequestOwnUpdateView(LoginRequiredMixin, FormView):
    model = QualificationRequest
    form_class = QualificationRequestCreateForm
    template_name = "qualification_requests/qualification_requests_update_form.html"
    success_url = reverse_lazy("qualification_requests:qualification_requests_list_own")

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.user != request.user:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        return QualificationRequest.objects.get(pk=self.kwargs["pk"])
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"instance": self.object})
        return kwargs

    def form_valid(self, form):
        if self.object.status != "pending":
            messages.error(
                self.request,
                _("You cannot edit a qualification request that is not pending.")
            )
            return self.form_invalid(form)
        
        self.object.qualification = form.instance.qualification
        self.object.qualification_date = form.instance.qualification_date
        self.object.user_comment = form.instance.user_comment
        self.object.save()
        return super().form_valid(form)

class QualificationRequestCheckView(CustomPermissionRequiredMixin, FormView):
    model = QualificationRequest
    form_class = QualificationRequestCheckForm
    template_name = "qualification_requests/qualification_requests_check_form.html"
    success_url = reverse_lazy("qualification_requests:qualification_requests_list")
    permission_required = "core.change_userprofile"

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        return QualificationRequest.objects.get(pk=self.kwargs["pk"])
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"instance": self.object})
        return kwargs

    def form_valid(self, form):
        if self.object.status != "pending":
            messages.error(
                self.request,
                _("You cannot edit a qualification request that is not pending.")
            )
            return self.form_invalid(form)
        
        self.object.qualification = form.instance.qualification
        self.object.qualification_date = form.instance.qualification_date
        self.object.expiration_date = form.instance.expiration_date
        self.object.reason = form.instance.reason
        self.object.save()

        action = self.request.POST.get("action")
        if action == "approve":
            form.instance.status = "approved"
            form.instance.save()
            messages.success(self.request, _("Qualification request approved."))
            self.grant_qualification()
        elif action == "reject":
            form.instance.status = "rejected"
            form.instance.save()
            messages.success(self.request, _("Qualification request rejected."))
        return super().form_valid(form)
    
    def grant_qualification(self):
        """Grant the qualification to the user if the request is approved."""
        if self.object.status == "approved":
            return QualificationGrant.objects.get_or_create(
                user=self.object.user,
                qualification=self.object.qualification,
                expires=self.object.expiration_date if self.object.expiration_date else None,
            )

class QualificationRequestOwnDeleteView(LoginRequiredMixin, DeleteView):
    model = QualificationRequest
    template_name = "qualification_requests/qualification_requests_delete_form.html"
    success_url = reverse_lazy("qualification_requests:qualification_requests_list_own")

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()

        if self.object.user != request.user:
            return HttpResponseForbidden(_("You have no rights to delete this request."))

        if self.object.status == "pending":
            messages.error(
                self.request,
                _("You cannot delete a qualification request that is pending.")
            )
            return HttpResponseRedirect(self.success_url)
        
        self.object.delete()
        messages.success(
            request,
            _("Qualification request deleted.")
        )
        return HttpResponseRedirect(self.success_url)

class QualificationRequestDeleteView(CustomPermissionRequiredMixin, DeleteView):
    model = QualificationRequest
    template_name = "qualification_requests/qualification_requests_delete_form.html"
    success_url = reverse_lazy("qualification_requests:qualification_requests_list")
    permission_required = "core.change_userprofile"
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()

        if self.object.status == "pending":
            messages.error(
                self.request,
                _("You cannot delete a qualification request that is pending.")
            )
            return HttpResponseRedirect(self.success_url)
        
        self.object.delete()
        messages.success(
            request,
            _("Qualification request deleted.")
        )
        return HttpResponseRedirect(self.success_url)