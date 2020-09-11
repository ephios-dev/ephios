from bootstrap4.widgets import RadioSelectButtonGroup
from django import forms
from django.template.loader import get_template
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, TemplateView
from django.views.generic.detail import SingleObjectMixin

from contrib.signup.instant import SimpleQualificationsRequiredSignupMethod
from event_management.models import AbstractParticipation, Shift
from guardian.mixins import PermissionRequiredMixin


class RequestConfirmView(PermissionRequiredMixin, SingleObjectMixin, FormView):
    model = Shift
    permission_required = "event_management.change_event"
    accept_global_perms = True
    template_name = "jepcontrib/signup_requestconfirm_disposition.html"

    def get_permission_object(self):
        self.object: Shift = self.get_object()
        return self.object.event

    def _get_participations_by_hash(self):
        for participation in self.object.get_participations(
            with_state_in={AbstractParticipation.REQUESTED, AbstractParticipation.CONFIRMED}
        ):
            yield str(hash(participation.participator)), participation

    def get_form(self, form_class=None):
        form = forms.Form(self.request.POST or None)
        for key, participation in self._get_participations_by_hash():
            form.fields[key] = forms.ChoiceField(
                label=f"{participation.participator!s}: ⁣",
                choices=AbstractParticipation.STATE_CHOICES,
                widget=RadioSelectButtonGroup,
                initial=participation.state,
            )
        return form

    def form_valid(self, form):
        for key, participation in self._get_participations_by_hash():
            participation.state = form.cleaned_data[key]
            participation.save()
        return super().form_valid(form)

    def get_success_url(self):
        return self.object.event.get_absolute_url()


class RequestConfirmSignupMethod(SimpleQualificationsRequiredSignupMethod):
    slug = "request_confirm"
    verbose_name = _("Request and confirm")
    description = _(
        """This method lets people request participation. Responsibles can then confirm the participation."""
    )
    registration_button_text = _("Request")
    signup_success_message = _("You have successfully requested a participation for {shift}.")
    signup_error_message = _("Requesting a participation failed: {error}")

    def render_shift_state(self, request):
        participations = self.shift.get_participations(
            with_state_in={AbstractParticipation.REQUESTED, AbstractParticipation.CONFIRMED}
        )
        return get_template("jepcontrib/signup_requestconfirm_state.html").render(
            {
                "shift": self.shift,
                "requested_participators": (
                    p.participator
                    for p in participations.filter(state=AbstractParticipation.REQUESTED)
                ),
                "confirmed_participators": (
                    p.participator
                    for p in participations.filter(state=AbstractParticipation.CONFIRMED)
                ),
                "disposition_url": (
                    reverse(
                        "contrib:shift_disposition_requestconfirm", kwargs=dict(pk=self.shift.pk)
                    )
                    if request.user.has_perm("event_management.change_event", obj=self.shift.event)
                    else None
                ),
            }
        )

    def perform_signup(self, participator, **kwargs):
        participation = super().perform_signup(participator, **kwargs)
        participation.state = AbstractParticipation.REQUESTED
        participation.save()
        return participation
