from django import forms
from django.utils.translation import gettext_lazy as _
from django_select2.forms import ModelSelect2Widget

from ephios.core.models import Qualification
from ephios.plugins.qualification_requests.models import QualificationRequest

class QualificationRequestAddForm(forms.ModelForm):
    class Meta:
        model = QualificationRequest
        fields = [
            "qualification",
            "qualification_date",
            "user_comment"
        ]
        widgets = {
            "qualification": ModelSelect2Widget(
                model=Qualification.objects.all(),
                search_fields=["title__icontains", "abbreviation__icontains"],
                attrs={
                    "data-placeholder": _("Select Qualification"),
                },
            ),
            "qualification_date": forms.DateInput(attrs={"type": "date"}),
            "user_comment": forms.Textarea(attrs={"rows": 4}),
        }

class QualificationRequestCheckForm(forms.ModelForm):

    created_at = forms.DateTimeField(
        label=_("Created At"),
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "readonly": "readonly"}),
        required=False,
    )

    class Meta:
        model = QualificationRequest
        fields = [
            "user",
            "qualification",
            "qualification_date",
            "expiration_date",
            "user_comment",
            "status"
        ]
        widgets = {
            "user": forms.TextInput(attrs={"readonly": "readonly"}),
            "qualification": forms.TextInput(attrs={"readonly": "readonly"}),
            "qualification_date": forms.DateInput(attrs={"type": "date", "readonly": "readonly"}),
            "expiration_date": forms.DateInput(attrs={"type": "date"}),
            "user_comment": forms.Textarea(attrs={"rows": 4, "readonly": "readonly"}),
            "status": forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["created_at"].initial = self.instance.created_at