from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import FileInput, Form, ModelForm, ModelMultipleChoiceField
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext as _
from django_select2.forms import Select2MultipleWidget

from ephios.core.forms.events import BasePluginFormMixin
from ephios.plugins.files.models import Document


class DocumentForm(ModelForm):
    class Meta:
        model = Document
        fields = ["title", "file"]
        widgets = {"file": FileInput(attrs={"accept": ".pdf"})}

    def clean_file(self):
        file_size = self.cleaned_data["file"].size
        if file_size > settings.GET_USERCONTENT_QUOTA():
            raise ValidationError(
                _("The file is too large. There are only %(quota)s available."),
                params={"quota": filesizeformat(settings.GET_USERCONTENT_QUOTA())},
            )
        return self.cleaned_data["file"]


class EventAttachedDocumentForm(BasePluginFormMixin, Form):
    documents = ModelMultipleChoiceField(
        queryset=Document.objects.all(), required=False, widget=Select2MultipleWidget
    )

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("prefix", "files")
        self.event = kwargs.pop("event")
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        self.fields["documents"].initial = (
            self.event.documents.all() if self.event and self.event.pk else []
        )

    def save(self):
        if self.cleaned_data["documents"]:
            self.event.documents.set(self.cleaned_data["documents"])

    @property
    def heading(self):
        return _("Attach files")

    def is_function_active(self):
        return self.event and self.event.documents.exists()
