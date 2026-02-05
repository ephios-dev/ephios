from functools import cached_property
from operator import attrgetter

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.timezone import localtime
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext_lazy
from django.views.generic import DetailView, FormView, ListView, RedirectView
from django.views.generic.detail import SingleObjectMixin
from django_select2.forms import Select2MultipleWidget
from guardian.shortcuts import get_objects_for_user, get_users_with_perms

from ephios.core.models import AbstractParticipation, Notification
from ephios.core.services.notifications.types import (
    CustomEventNotification,
    GenericMassNotification,
)
from ephios.extra.mixins import CustomCheckPermissionMixin


class OwnNotificationMixin(LoginRequiredMixin):
    model = Notification

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by("-created_at")


class NotificationListView(OwnNotificationMixin, ListView):
    paginate_by = 20


class NotificationDetailView(OwnNotificationMixin, DetailView):
    pass


class NotificationMarkAsReadView(OwnNotificationMixin, SingleObjectMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        notification = self.get_object()
        notification.read = True
        notification.save()
        return reverse("core:notification_list")


class NotificationMarkAllAsReadView(LoginRequiredMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        Notification.objects.filter(user=self.request.user).update(read=True)
        return reverse("core:notification_list")


class MassNotificationForm(forms.Form):
    subject = forms.CharField(
        label=_("Subject"),
    )
    body = forms.CharField(
        label=_("Message"),
        widget=forms.Textarea(attrs={"rows": 8}),
    )
    to_participants = forms.MultipleChoiceField(
        label=_("Recipients"),
        widget=Select2MultipleWidget(
            attrs={
                "data-placeholder": _("Add recipients"),
                "data-allow-clear": "true",
            },
        ),
        choices=[],  # added in __init__
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        self.event = kwargs.pop("event", None)
        super().__init__(*args, **kwargs)
        self._configure_choices()
        if self.event:
            self.fields["body"].widget.attrs["placeholder"] = _(
                "Hello,\n\nregarding {event_title} starting at {event_start} we want to communicate...\n\nKind regards\n"
            ).format(
                event_title=self.event.title,
                event_start=date_format(
                    localtime(self.event.get_start_time()), "SHORT_DATETIME_FORMAT"
                ),
            ) + str(self.request.user)
            self.fields["to_participants"].help_text = _(
                "You can only select users that have permission to view the event."
            )

    def _configure_choices(self):
        choices = {}
        self.participants_by_identifier = {}

        # without event context, a user can send notifications to profiles they can see
        user_qs = get_objects_for_user(user=self.request.user, perms=["core.view_userprofile"])
        if self.event:
            # if we are planning for an event, we can reach users that can view the event
            user_qs = get_users_with_perms(self.event, only_with_perms_in=["view_event"])
        for user in user_qs:
            participant = user.as_participant()
            choices[participant.identifier] = str(participant)
            self.participants_by_identifier[participant.identifier] = participant

        self.event_confirmed = set()
        self.event_requested = set()
        self.event_nonfeedback = set(choices.keys())
        if self.event:
            event_participations = AbstractParticipation.objects.filter(
                shift__event=self.event,
            )
            for participation in event_participations:
                participant = participation.participant
                if not participant.email:
                    continue  # doesn't make sense to include participants we don't have email for like Placeholders

                self.event_nonfeedback -= {participant.identifier}
                match participation.state:
                    case AbstractParticipation.States.CONFIRMED:
                        self.event_confirmed.add(participant.identifier)
                    case AbstractParticipation.States.REQUESTED:
                        self.event_requested.add(participant.identifier)
                choices[participant.identifier] = str(participant)
                self.participants_by_identifier[participant.identifier] = participant

        # because a participant might be in multiple participations states with multiple shifts,
        # we adjust the sets to have them in the most important group
        self.event_requested -= self.event_confirmed

        sorted_names = sorted(choices.values())

        def sort_key(item):
            identifier, name = item
            if identifier in self.event_confirmed:
                return -len(sorted_names) + sorted_names.index(name)
            if identifier in self.event_requested:
                return sorted_names.index(name)
            return len(sorted_names) + sorted_names.index(name)

        choices = list(sorted(choices.items(), key=sort_key))

        if self.event:
            optgroup_choices = {
                _("confirmed"): {i: p for i, p in choices if i in self.event_confirmed},
                _("requested"): {i: p for i, p in choices if i in self.event_requested},
                _("without response"): {i: p for i, p in choices if i in self.event_nonfeedback},
                _("others"): {
                    i: p
                    for i, p in choices
                    if i not in self.event_confirmed | self.event_requested | self.event_nonfeedback
                },
            }
        else:
            optgroup_choices = choices

        self.fields["to_participants"].choices = optgroup_choices

    def clean_to_participants(self):
        return list(map(self.participants_by_identifier.get, self.cleaned_data["to_participants"]))


class MassNotificationWriteView(CustomCheckPermissionMixin, FormView):
    form_class = MassNotificationForm
    template_name = "core/mass_notification_write.html"

    def has_permission(self):
        # either has permission "core.view_userprofile"
        # or event is given and user is responsible
        if not self.request.user.is_authenticated:
            return False
        if self.event and self.request.user.has_perm("core.change_event", obj=self.event):
            return True
        return self.request.user.has_perm("core.view_userprofile")

    @cached_property
    def event(self):
        return (
            get_objects_for_user(self.request.user, ["core.change_event"])
            .filter(id=self.request.GET.get("event_id", None))
            .first()
        )

    def get_context_data(self, **kwargs):
        return super().get_context_data(cancel_url=self.get_success_url(), **kwargs)

    def get_form_kwargs(self):
        return {"request": self.request, "event": self.event, **super().get_form_kwargs()}

    def get_initial(self):
        initial = {}
        if self.event:
            initial["subject"] = _("Information on {event_title}").format(
                event_title=self.event.title
            )
        initial["to_participants"] = self.request.GET.getlist("to", [])
        return initial

    def form_valid(self, form):
        subject_and_body = {
            "subject": form.cleaned_data["subject"],
            "body": form.cleaned_data["body"],
        }
        recipients = form.cleaned_data["to_participants"]
        if self.event:
            CustomEventNotification.send(self.event, recipients, **subject_and_body)
            messages.success(
                self.request,
                ngettext_lazy(
                    "Sent notification to {count} participant.",
                    "Sent notification to {count} participants.",
                    len(recipients),
                ).format(count=len(recipients)),
            )
        else:
            GenericMassNotification.send(
                users=list(map(attrgetter("user"), recipients)),
                **subject_and_body,
            )
            messages.success(
                self.request,
                ngettext_lazy(
                    "Sent notification to {count} user.",
                    "Sent notification to {count} users.",
                    len(recipients),
                ).format(count=len(recipients)),
            )
        return redirect(self.get_success_url())

    def get_success_url(self):
        if self.event:
            return self.event.get_absolute_url()
        return reverse("core:userprofile_list")
