from django import forms
from django.shortcuts import redirect
from django.template.loader import get_template
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django.views.generic.detail import SingleObjectMixin
from django_select2.forms import Select2MultipleWidget

from ephios.event_management.models import AbstractParticipation, Shift
from ephios.event_management.signup import BaseSignupMethod, ParticipationError
from ephios.extra.permissions import CustomPermissionRequiredMixin
from ephios.user_management.models import Qualification


class SimpleQualificationsRequiredSignupMethod(BaseSignupMethod):
    # pylint: disable=abstract-method
    def __init__(self, shift):
        super().__init__(shift)
        if shift is not None:
            self.configuration.required_qualifications = Qualification.objects.filter(
                pk__in=self.configuration.required_qualification_ids
            )

    @property
    def signup_checkers(self):
        return super().signup_checkers + [self.check_qualification]

    @staticmethod
    def check_qualification(method, participant):
        if not participant.has_qualifications(method.configuration.required_qualifications):
            return ParticipationError(_("You are not qualified."))

    def get_configuration_fields(self):
        return {
            **super().get_configuration_fields(),
            "required_qualification_ids": {
                "formfield": forms.ModelMultipleChoiceField(
                    label=_("Required Qualifications"),
                    queryset=Qualification.objects.all(),
                    widget=Select2MultipleWidget,
                    required=False,
                ),
                "default": [],
                "publish_with_label": _("Required Qualification"),
                "format": lambda ids: ", ".join(
                    Qualification.objects.filter(id__in=ids).values_list("title", flat=True)
                ),
            },
        }


class InstantConfirmationSignupMethod(SimpleQualificationsRequiredSignupMethod):
    slug = "instant_confirmation"
    verbose_name = _("Instant Confirmation")
    description = _("""This method instantly confirms every signup after it was requested.""")

    @property
    def signup_checkers(self):
        return super().signup_checkers + [self.check_maximum_number_of_participants]

    @staticmethod
    def check_maximum_number_of_participants(method, participant):
        if method.configuration.maximum_number_of_participants is not None:
            current_count = AbstractParticipation.objects.filter(
                shift=method.shift, state=AbstractParticipation.States.CONFIRMED
            ).count()
            if current_count >= method.configuration.maximum_number_of_participants:
                return ParticipationError(_("The maximum number of participants is reached."))

    def get_configuration_fields(self):
        return {
            **super().get_configuration_fields(),
            "maximum_number_of_participants": {
                "formfield": forms.IntegerField(min_value=1, required=False),
                "default": None,
                "publish_with_label": _("Maximum number of participants"),
            },
        }

    def render_shift_state(self, request):
        return get_template("basesignup/signup_instant_state.html").render({"shift": self.shift})

    def perform_signup(self, participant, **kwargs):
        participation = super().perform_signup(participant, **kwargs)
        participation.state = AbstractParticipation.States.CONFIRMED
        participation.save()
        return participation


DispositionParticipationFormset = forms.modelformset_factory(
    model=AbstractParticipation,
    fields=["state"],
    extra=0,
    can_order=False,
    can_delete=False,
    widgets={
        "state": forms.HiddenInput(attrs={"class": "state-input"}),
    },
)


class RequestConfirmDispositionView(CustomPermissionRequiredMixin, SingleObjectMixin, TemplateView):
    model = Shift
    permission_required = "event_management.change_event"
    template_name = "basesignup/requestconfirm/disposition.html"

    def get_permission_object(self):
        self.object: Shift = self.get_object()
        return self.object.event

    def get_formset(self):
        return DispositionParticipationFormset(
            self.request.POST or None, queryset=self.object.participations
        )

    def get(self, request, *args, **kwargs):
        self.object: Shift = self.get_object()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object: Shift = self.get_object()
        formset = self.get_formset()
        if formset.is_valid():
            formset.save()
            return redirect(self.object.event.get_absolute_url())
        return self.get(request, *args, **kwargs, formset=formset)

    def get_context_data(self, **kwargs):
        kwargs.setdefault("formset", self.get_formset())
        kwargs.setdefault("states", AbstractParticipation.States)
        return super().get_context_data(**kwargs)


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
        participations = self.shift.participations.filter(
            state__in={
                AbstractParticipation.States.REQUESTED,
                AbstractParticipation.States.CONFIRMED,
            }
        )
        return get_template("basesignup/requestconfirm/fragment_state.html").render(
            {
                "shift": self.shift,
                "requested_participants": (
                    p.participant
                    for p in participations.filter(state=AbstractParticipation.States.REQUESTED)
                ),
                "confirmed_participants": (
                    p.participant
                    for p in participations.filter(state=AbstractParticipation.States.CONFIRMED)
                ),
                "disposition_url": (
                    reverse(
                        "basesignup:shift_disposition_requestconfirm", kwargs=dict(pk=self.shift.pk)
                    )
                    if request.user.has_perm("event_management.change_event", obj=self.shift.event)
                    else None
                ),
            }
        )

    def perform_signup(self, participant, **kwargs):
        participation = super().perform_signup(participant, **kwargs)
        participation.state = AbstractParticipation.States.REQUESTED
        participation.save()
        return participation
