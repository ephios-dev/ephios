from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML
from django import forms
from django.utils.translation import gettext_lazy as _
from django_select2.forms import Select2Widget

from ephios.core.forms.events import BaseEventPluginFormMixin
from ephios.extra.widgets import CustomDateInput
from ephios.plugins.eventautoqualification.models import EventAutoQualificationConfiguration


class EventAutoQualificationForm(BaseEventPluginFormMixin, forms.ModelForm):
    class Meta:
        model = EventAutoQualificationConfiguration
        fields = ["qualification", "expiration_date", "mode", "extend_only", "needs_confirmation"]
        widgets = {
            "qualification": Select2Widget,
            "expiration_date": CustomDateInput(format="%Y-%m-%d"),
        }

    def __init__(self, *args, event=None, edit_permission=False, **kwargs):
        kwargs.setdefault("prefix", "autoqualification")
        self.event = event
        try:
            kwargs.setdefault(
                "instance", EventAutoQualificationConfiguration.objects.get(event=self.event)
            )
        except EventAutoQualificationConfiguration.DoesNotExist:
            pass

        super().__init__(*args, **kwargs)

        self.fields["qualification"].required = False
        self.helper = FormHelper(self)
        if not edit_permission:
            self.helper.layout.insert(
                0,
                HTML(
                    "<p>"
                    + str(
                        _(
                            "You don't have permission to grant qualifications, so you can't edit these settings."
                        )
                    )
                    + "</p>"
                ),
            )
            for field in self.fields.values():
                field.disabled = True

    def save(self, commit=True):
        if self.cleaned_data.get("qualification"):
            self.instance.event = self.event
            super().save(commit)
        elif self.instance.pk:
            self.instance.delete()

    @property
    def heading(self):
        return _("Automatic qualification")

    def is_function_active(self):
        return bool(self.instance.pk)
