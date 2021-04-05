from django import forms
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import QuerySet
from django.db.models.functions import Cast
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from django_select2.forms import Select2Widget

from ephios.core.models import UserProfile
from ephios.core.widgets import UserProfileWidget
from ephios.extra.mixins import CustomPermissionRequiredMixin
from ephios.extra.widgets import CustomDateInput
from ephios.modellogging.models import LogEntry


class LogFilterForm(forms.Form):
    object_type = forms.ChoiceField(
        choices=[("", "---------")],
        required=False,
        label=_("Concerns"),
        widget=Select2Widget,
        error_messages={
            "invalid_choice": _("%(value)s does not have any associated entries."),
        },
    )
    object_id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    user = forms.ModelChoiceField(
        queryset=UserProfile.objects.all(),
        widget=UserProfileWidget,
        required=False,
        label=_("Acting User"),
    )
    date = forms.DateField(
        widget=CustomDateInput(format="%Y-%m-%d"), required=False, label=_("Date")
    )
    search = forms.CharField(
        required=False,
        label=_("Contents"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.content_types = {}
        qs: QuerySet[ContentType] = ContentType.objects.filter(
            pk__in=LogEntry.objects.values_list("attached_to_object_type", flat=True)
        )
        for content_type in qs:
            key = content_type.model.lower()
            self.fields["object_type"].choices.append(
                (key, content_type.model_class()._meta.verbose_name_plural)
            )
            self.content_types[key] = content_type
        self.fields["object_type"].widget.choices = self.fields["object_type"].choices

    def filter(self, queryset):
        if not self.is_valid():
            return queryset

        kw = {}
        if object_type := self.cleaned_data.get("object_type"):
            kw["attached_to_object_type"] = self.content_types[object_type]
        if object_id := self.cleaned_data.get("object_id"):
            kw["attached_to_object_id"] = object_id
        if user := self.cleaned_data.get("user"):
            kw["user"] = user
        if date := self.cleaned_data.get("date"):
            kw["datetime__date"] = date

        queryset = queryset.filter(**kw)

        if search := self.cleaned_data.get("search"):
            queryset = queryset.annotate(
                data_string=Cast("data", output_field=models.TextField()),
            ).filter(data_string__icontains=search)

        return queryset

    @cached_property
    def content_object(self):
        if not self.is_valid():
            return None
        if (object_type := self.cleaned_data.get("object_type")) and (
            object_id := self.cleaned_data.get("object_id")
        ):
            return self.content_types[object_type].get_object_for_this_type(id=object_id)


class LogView(CustomPermissionRequiredMixin, ListView):
    template_name = "core/logentry_list.html"
    model = LogEntry
    permission_required = "modellogging.view_logentry"
    paginate_by = 20

    @cached_property
    def filter_form(self):
        return LogFilterForm(self.request.GET or None)

    def get_context_data(self, **kwargs):
        return super().get_context_data(filter_form=self.filter_form, **kwargs)

    def get_queryset(self):
        return self.filter_form.filter(super().get_queryset())
