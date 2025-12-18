from build.lib.guardian.shortcuts import get_objects_for_user
from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, FormView, ListView, RedirectView
from django.views.generic.detail import SingleObjectMixin
from django_select2.forms import ModelSelect2MultipleWidget

from ephios.core.models import AbstractParticipation, Notification, UserProfile
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
        widget=forms.Textarea(attrs={"rows": 5}),
    )
    to_users = forms.ModelMultipleChoiceField(
        widget=ModelSelect2MultipleWidget(
            model=UserProfile,
            search_fields=["display_name__icontains"],
            attrs={
                "data-placeholder": _("search"),
            },
        ),
        queryset=UserProfile.objects.none(),  # TODO set using __init__
    )
    to_participations = forms.ModelMultipleChoiceField(
        widget=ModelSelect2MultipleWidget(
            model=AbstractParticipation,
            search_fields=[],  # TODO
        ),
        queryset=AbstractParticipation.objects.none(),  # TODO set
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        self.event = kwargs.pop("event", None)
        super().__init__(*args, **kwargs)
        self._configure_choice_querysets()

    def _configure_choice_querysets(self):
        allowed_users = set(
            get_objects_for_user(user=self.request.user, perms=["core.view_userprofile"])
        )
        allowed_participations = set()
        if self.event:
            allowed_participations |= set(
                AbstractParticipation.objects.filter(shift__event=self.event)
            )
            allowed_users |= {u for p in allowed_participations if (u := getattr(p, "user", None))}
        self.fields["to_users"].queryset = UserProfile.objects.filter(
            is_active=True, pk__in=[u.pk for u in allowed_users]
        )
        self.fields["to_participations"].queryset = AbstractParticipation.objects.filter(
            pk__in=[p.pk for p in allowed_participations]
        )


class MassNotificationWriteView(CustomCheckPermissionMixin, FormView):
    """
    - [] next url parameter, get from target object?
    - [] permission check based on target object?
    """

    form_class = MassNotificationForm
    template_name = "core/mass_notification_write.html"
    permission_required = "core.view_userprofile"

    def get_form_kwargs(self):
        event = (
            get_objects_for_user(self.request.user, "core:change_event")
            .filter(id=self.request.GET.get("event_id", None))
            .first()
        )
        return {"request": self.request, "event": event, **super().get_form_kwargs()}

    def get_initial(self):
        return {
            # subject and body from notification type? How to deal with placeholders?
            # receipients based on GET parameter? or implement it here?
        }
