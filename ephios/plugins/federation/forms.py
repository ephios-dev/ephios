from django import forms
from django.utils.translation import gettext as _
from django_select2.forms import Select2MultipleWidget

from ephios.core.forms.events import BasePluginFormMixin
from ephios.plugins.federation.models import FederatedEventShare, FederatedGuest


class EventAllowFederationForm(BasePluginFormMixin, forms.Form):
    shared_with = forms.ModelMultipleChoiceField(
        queryset=FederatedGuest.objects.all(), required=False, widget=Select2MultipleWidget
    )

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("prefix", "guests")
        self.event = kwargs.pop("event")
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        try:
            self.instance = FederatedEventShare.objects.get(event_id=self.event.id)
        except (AttributeError, FederatedEventShare.DoesNotExist):
            self.instance = FederatedEventShare(event=self.event)
        self.fields["shared_with"].initial = self.instance.shared_with.all()

    def save(self):
        self.instance.shared_with.set(self.cleaned_data["shared_with"])

    @property
    def heading(self):
        return _("Federation")

    def is_function_active(self):
        return self.instance.shared_with.exists()
