from django import forms
from django.utils.translation import gettext_lazy as _
from django_select2.forms import ModelSelect2Widget

from ephios.core.models import Qualification
from ephios.plugins.qualification_requests.models import QualificationRequest

class QualificationRequestForm(forms.ModelForm):
    class Meta:
        model = QualificationRequest
        fields = ["user", "qualification", "qualification_date", "expiration_date", "status"]
        widgets = {
            "qualification": ModelSelect2Widget(
                model=Qualification.objects.all(),
                search_fields=["title__icontains", "abbreviation__icontains"],
                attrs={
                    "data-placeholder": _("Select Qualification"),
                    "style": "width: 100%;",
                },
            ),
            "qualification_date": forms.DateInput(attrs={"type": "date"}),
            "expiration_date": forms.DateInput(attrs={"type": "date"}),
            "requested_at": forms.DateInput(attrs={"type": "date"}),
        }