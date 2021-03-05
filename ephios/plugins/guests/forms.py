from django import forms
from django.contrib import messages
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from ephios.core.forms.events import BaseEventPluginForm
from ephios.plugins.guests.models import EventGuestShare


class EventAllowGuestsForm(BaseEventPluginForm):
    active = forms.BooleanField(label=_("Allow guests"), required=False)
    link = forms.CharField(disabled=True, label="Link for guest registration", required=False)
    new_link = forms.BooleanField(label=_("Generate a new link when saving"), required=False)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("prefix", "guests")
        self.event = kwargs.pop("event")
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        share, __ = EventGuestShare.objects.get_or_create(event=self.event)
        self.fields["link"].initial = share.url
        self.fields["active"].initial = share.active

    def save(self):
        share, __ = EventGuestShare.objects.get_or_create(event=self.event)
        if self.cleaned_data["new_link"]:
            share.new_token()
        share.active = self.cleaned_data["active"]
        if self.cleaned_data["active"]:
            messages.info(
                self.request,
                mark_safe(
                    _("Guests can sign up for this event <a href={href}>here</a>. ").format(
                        href=share.url
                    )
                ),
            )
        share.save()

    @property
    def heading(self):
        return _("Guests")
