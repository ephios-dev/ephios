from functools import cached_property

from build.lib.guardian.shortcuts import get_objects_for_user
from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.timezone import localtime
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, FormView, ListView, RedirectView
from django.views.generic.detail import SingleObjectMixin
from django_select2.forms import Select2MultipleWidget

from ephios.core.models import AbstractParticipation, Notification
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
    subject = forms.CharField()
    body = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 8}),
    )
    to_participants = forms.MultipleChoiceField(
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

    def _configure_choices(self):
        choices = {}
        self.participants_by_identifier = {}
        for user in get_objects_for_user(user=self.request.user, perms=["core.view_userprofile"]):
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
        self.event_nonfeedback -= self.event_confirmed | self.event_requested
        self.event_requested -= self.event_confirmed

        sorted_names = sorted(choices.values())

        def sort_key(item):
            identifier, name = item
            if identifier in self.event_confirmed:
                return -len(sorted_names) + sorted_names.index(name)
            if identifier in self.event_requested:
                return sorted_names.index(name)
            return len(sorted_names) + sorted_names.index(name)

        self.fields["to_participants"].choices = sorted(choices.items(), key=sort_key)

    def clean_to_participants(self):
        return list(map(self.participants_by_identifier.get, self.cleaned_data["to_participants"]))


class MassNotificationWriteView(CustomCheckPermissionMixin, FormView):
    """
    - [] next url parameter, get from target object?
    - [] permission check based on target object?
    """

    form_class = MassNotificationForm
    template_name = "core/mass_notification_write.html"

    def has_permission(self):
        # either has permission "core.view_userprofile"
        # or event is given and user is responsible
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
            initial["body"] = _(
                "Hello,\n\nregarding {event_title} starting at {event_start} we want to communicate...\n\nKind regards\n"
            ).format(
                event_title=self.event.title,
                event_start=date_format(
                    localtime(self.event.get_start_time()), "SHORT_DATETIME_FORMAT"
                ),
            )
        return initial

    def form_valid(self, form):
        for participant in form.cleaned_data["to_participants"]:
            confirmed_or_requested = participant.identifier in (
                form.event_confirmed | form.event_requested
            )
            # send notifications

        return redirect(self.get_success_url())

    def get_success_url(self):
        if self.event:
            return self.event.get_absolute_url()
        return reverse("core:home")
