from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.db.models import Count, Exists, OuterRef, Prefetch, Q, QuerySet
from django.urls import reverse_lazy
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, FormView
from django.views.generic.detail import SingleObjectMixin
from django_select2.forms import ModelSelect2Widget, Select2Widget

from ephios.core.models import Qualification
from ephios.extra.mixins import CustomPermissionRequiredMixin
from ephios.plugins.qualification_requests.forms import QualificationRequestForm
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

class QualificationRequestAddView(LoginRequiredMixin, FormView):
    model = QualificationRequest
    form_class = QualificationRequestForm
    template_name = "qualification_requests/qualification_requests_form.html"
    success_url = reverse_lazy("qualification_requests:qualification_requests_list_own")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"initial": {"user": self.request.user}})
        return kwargs

    def form_valid(self, form):
        qualification_request = QualificationRequest.objects.create(
            user=self.request.user,
            qualification=form.instance.qualification,
            qualification_date=form.instance.qualification_date
        )

        print(f"Created qualification request: {qualification_request}")

        return super().form_valid(form)

class QualificationRequestUpdateView(LoginRequiredMixin, FormView):
    model = QualificationRequest
    form_class = QualificationRequestForm
    template_name = "qualification_requests/qualification_requests_form.html"
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
        self.object.qualification = form.instance.qualification
        self.object.qualification_date = form.instance.qualification_date
        self.object.save()
        return super().form_valid(form)