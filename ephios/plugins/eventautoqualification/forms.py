from django import forms
from django.utils.translation import gettext_lazy as _
from django_select2.forms import Select2Widget

from ephios.core.forms.events import BasePluginFormMixin
from ephios.extra.widgets import CustomDateInput
from ephios.plugins.eventautoqualification.models import EventAutoQualificationConfiguration


class EventAutoQualificationForm(BasePluginFormMixin, forms.ModelForm):
    template_name = "eventautoqualification/auto_qualification_setup_form.html"

    class Meta:
        model = EventAutoQualificationConfiguration
        fields = ["qualification", "expiration_date", "mode", "extend_only", "needs_confirmation"]
        widgets = {
            "qualification": Select2Widget,
            "expiration_date": CustomDateInput,
        }

    def __init__(self, *args, event=None, edit_permission=False, **kwargs):
        kwargs.setdefault("prefix", "autoqualification")
        self.event = event
        try:
            kwargs.setdefault(
                "instance", EventAutoQualificationConfiguration.objects.get(event_id=self.event.id)
            )
        except (AttributeError, EventAutoQualificationConfiguration.DoesNotExist):
            pass

        super().__init__(*args, **kwargs)

        self.fields["qualification"].required = False
        self.edit_permission = edit_permission
        if not edit_permission:
            for field in self.fields.values():
                field.disabled = True

    def get_context(self):
        context = super().get_context()
        context["edit_permission"] = self.edit_permission
        return context

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
