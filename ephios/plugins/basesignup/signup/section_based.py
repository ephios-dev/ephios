import uuid

from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import redirect
from django.template.loader import get_template
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from django_select2.forms import Select2MultipleWidget

from ephios.event_management.signup import (
    AbstractParticipant,
    BaseSignupMethod,
    BaseSignupView,
    ParticipationError,
)
from ephios.plugins.basesignup.signup import RequestConfirmDispositionView
from ephios.user_management.models import Qualification


class SectionBasedDispositionView(RequestConfirmDispositionView):
    pass


class SectionForm(forms.Form):
    title = forms.CharField(label=_("Title"), required=True)
    qualifications = forms.ModelMultipleChoiceField(
        label=_("Required Qualifications"),
        queryset=Qualification.objects.all(),
        widget=Select2MultipleWidget,
        required=False,
    )
    min_count = forms.IntegerField(label=_("min amount"), min_value=1, required=True)
    uuid = forms.CharField(widget=forms.HiddenInput, required=False)

    def clean_uuid(self):
        return self.cleaned_data.get("uuid") or uuid.uuid4()


SectionsFormset = forms.formset_factory(
    SectionForm, can_delete=True, min_num=1, validate_min=1, extra=0
)


class SectionBasedConfigurationForm(forms.Form):
    def __init__(self, data=None, **kwargs):
        super().__init__(data, **kwargs)
        self.sections_formset = SectionsFormset(
            data=data,
            initial=self.initial.get("sections", list()),
            prefix="sections",
        )

    def clean_sections(self):
        if not self.sections_formset.is_valid():
            raise ValidationError(_("The sections aren't configured correctly."))

        sections = [
            {
                key: form.cleaned_data[key]
                for key in ("title", "qualifications", "min_count", "uuid")
            }
            for form in self.sections_formset
        ]
        return sections


class SectionSignupForm(forms.Form):
    section = forms.ChoiceField(
        label=_("Preferred Section"),
        widget=forms.RadioSelect,
        # choices are set as (uuid, title) of section
    )


class SectionBasedSignupView(FormView, BaseSignupView):

    template_name = "basesignup/section_based/signup.html"

    def get_form(self, form_class=None):
        form = SectionSignupForm(self.request.POST)
        form.fields["section"].choices = [
            (section["uuid"], section["title"]) for section in self.method.configuration.sections
        ]
        return form

    def get_context_data(self, **kwargs):
        kwargs.setdefault("shift", self.shift)
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        try:
            with transaction.atomic():
                self.method.perform_signup(
                    self.request.user.as_participant(),
                    preferred_section_uuid=form.cleaned_data["section"],
                )
                messages.success(
                    self.request,
                    self.method.signup_success_message.format(shift=self.shift),
                )
        except ParticipationError as errors:
            for error in errors:
                messages.error(self.request, self.method.signup_error_message.format(error=error))
        return redirect(self.shift.event.get_absolute_url())

    def signup_pressed(self, request, *args, **kwargs):
        if not self.method.configuration.choose_preferred_section:
            super().signup_pressed(request, *args, **kwargs)
        return redirect(reverse("event_management:shift_action", kwargs=dict(pk=self.shift.pk)))


class SectionBasedSignupMethod(BaseSignupMethod):
    slug = "section_based"
    verbose_name = _("Apply for sections")
    description = _(
        """This method lets you define sections for which people can choose from.
        Sections contain qualifications that helpers need to fulfil."""
    )
    registration_button_text = _("Request")
    signup_success_message = _("You have successfully requested a participation for {shift}.")
    signup_error_message = _("Requesting a participation failed: {error}")
    configuration_form_class = SectionBasedConfigurationForm
    signup_view_class = SectionBasedSignupView

    def get_configuration_fields(self):
        return {
            **super().get_configuration_fields(),
            "choose_preferred_section": {
                "formfield": forms.BooleanField(
                    label=_("Ask participants for a preferred section"),
                    help_text=_("This only makes sense if you configure multiple sections."),
                    widget=forms.CheckboxInput,
                    required=False,
                ),
                "default": False,
            },
            "sections": {
                "formfield": forms.Field(
                    label=_("Structure"),
                    widget=forms.HiddenInput,
                    required=False,
                ),
                "default": [],
            },
        }

    # TODO qualification checks for signup
    # TODO qualification checks for choosing a section

    # TODO disposition
    # TODO state display

    def perform_signup(self, participant: AbstractParticipant, preferred_section_uuid=None):
        participation = super().perform_signup(participant)
        participation.data["preferred_section_uuid"] = preferred_section_uuid
        participation.save()

    def render_configuration_form(self, *args, form=None, **kwargs):
        form = form or self.get_configuration_form(*args, **kwargs)
        template = get_template("basesignup/section_based/configuration_form.html").render(
            {"form": form}
        )
        return template

    def render_shift_state(self, request):
        return "this is the shift state"
