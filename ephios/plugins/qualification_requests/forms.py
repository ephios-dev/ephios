from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout, Submit
from django import forms
from django.utils.translation import gettext as _

from ephios.core.consequences import QualificationConsequenceHandler
from ephios.core.models import Qualification
from ephios.extra.widgets import CustomDateInput


class QualificationRequestForm(forms.Form):
    qualification = forms.ModelChoiceField(queryset=Qualification.objects.all())
    acquired = forms.DateField(widget=CustomDateInput)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Field("qualification"),
            Field("acquired"),
            FormActions(
                Submit("submit", _("Save"), css_class="float-end"),
            ),
        )

    def create_consequence(self):
        qualification = self.cleaned_data["qualification"]
        acquired = self.cleaned_data["acquired"]
        expires = None

        if qualification.default_expiration_time:
            expires = qualification.default_expiration_time.apply_to(acquired)

        QualificationConsequenceHandler.create(
            user=self.user,
            qualification=self.cleaned_data["qualification"],
            acquired=self.cleaned_data["acquired"] or None,
            expires=expires,
        )
