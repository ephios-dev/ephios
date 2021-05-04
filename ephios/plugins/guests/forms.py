from django import forms
from django.contrib import messages
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from ephios.core.forms.events import BaseEventPluginFormMixin
from ephios.plugins.guests.models import EventGuestShare


class EventAllowGuestsForm(BaseEventPluginFormMixin, forms.Form):
    active = forms.BooleanField(label=_("Allow guests"), required=False)
    link = forms.CharField(disabled=True, label="Link for guest registration", required=False)
    new_link = forms.BooleanField(label=_("Generate a new link when saving"), required=False)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("prefix", "guests")
        self.event = kwargs.pop("event")
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        try:
            self.instance = EventGuestShare.objects.get(event=self.event)
            self.fields["link"].initial = self.instance.url
        except EventGuestShare.DoesNotExist:
            self.instance = EventGuestShare(event=self.event)
            del self.fields["link"]
            del self.fields["new_link"]
        self.fields["active"].initial = self.instance.active

    def save(self):
        if self.cleaned_data.get("new_link"):
            self.instance.new_token()
        self.instance.active = self.cleaned_data["active"]
        if self.cleaned_data["active"]:
            messages.info(
                self.request,
                mark_safe(
                    _("Guests can sign up for this event <a href={href}>here</a>. ").format(
                        href=self.instance.url
                    )
                ),
            )
        self.instance.save()

    @property
    def heading(self):
        return _("Guests")

    def is_function_active(self):
        return self.instance.active
