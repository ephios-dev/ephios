from django import forms
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _
from django_select2.forms import Select2Widget

from ephios.extra.widgets import CustomDateInput
from ephios.plugins.qualification_requests.models import QualificationRequest

class QualificationRequestCreateForm(ModelForm):
    class Meta:
        model = QualificationRequest
        fields = [
            "qualification",
            "qualification_date",
            "user_comment",
        ]
        widgets = {
            "qualification": Select2Widget,
            "qualification_date": CustomDateInput,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Default auf "pending", wenn status nicht existiert
        status = getattr(self.instance, "status", "pending")
        if status != "pending":
            self.disable_fields(self.fields.keys())
    
    def disable_fields(self, field_names):
        """Helper function to disable multiple fields."""
        for field_name in field_names:
            self.fields[field_name].disabled = True

class QualificationRequestCheckForm(ModelForm):
    class Meta:
        model = QualificationRequest
        fields = [
            "user",
            "qualification",
            "qualification_date",
            "expiration_date",
            "user_comment",
            "status",
            "reason",
        ]
        widgets = {
            "qualification": Select2Widget,
            "qualification_date": CustomDateInput,
            "expiration_date": CustomDateInput,
        }
        help_texts = {
            "expiration_date": _("Leave empty for no expiration."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.status != "pending":
            self.disable_fields(self.fields.keys())
            return
        
        self.disable_fields([
            "user",
            "user_comment",
            "status",
        ])
    
    def disable_fields(self, field_names):
        """Helper function to disable multiple fields."""
        for field_name in field_names:
            self.fields[field_name].disabled = True