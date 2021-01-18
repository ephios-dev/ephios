import uuid
from functools import cached_property
from itertools import groupby
from operator import itemgetter

from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import redirect
from django.template.loader import get_template
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import FormView, TemplateView
from django.views.generic.base import TemplateResponseMixin
from django.views.generic.detail import SingleObjectMixin
from django_select2.forms import ModelSelect2Widget, Select2MultipleWidget

from ephios.event_management.models import AbstractParticipation, Shift
from ephios.event_management.signup import (
    AbstractParticipant,
    BaseSignupMethod,
    BaseSignupView,
    ParticipationError,
)
from ephios.extra.permissions import CustomPermissionRequiredMixin
from ephios.user_management.models import Qualification, UserProfile


def sections_participant_qualifies_for(sections, participant: AbstractParticipant):
    available_qualification_ids = set(q.id for q in participant.collect_all_qualifications())
    return [
        section
        for section in sections
        if set(section["qualifications"]) <= available_qualification_ids
    ]


class DispositionParticipationForm(forms.ModelForm):
    section = forms.ChoiceField(
        label=_("Section"), required=False  # only required if participation is confirmed
    )

    class Meta:
        model = AbstractParticipation
        fields = ["state"]
        widgets = dict(state=forms.HiddenInput(attrs={"class": "state-input"}))

    def __init__(self, shift, **kwargs):
        super().__init__(**kwargs)
        sections = shift.signup_method.configuration.sections
        qualified_sections = list(
            sections_participant_qualifies_for(
                sections,
                self.instance.participant,
            )
        )
        unqualified_sections = [
            section for section in sections if section not in qualified_sections
        ]
        self.fields["section"].choices = (
            ("", "---"),
            (
                _("qualified"),
                [(section["uuid"], section["title"]) for section in qualified_sections],
            )
            if qualified_sections
            else (),
            (
                _("unqualified"),
                [(section["uuid"], section["title"]) for section in unqualified_sections],
            )
            if unqualified_sections
            else (),
        )
        if preferred_section_uuid := self.instance.data.get("preferred_section_uuid"):
            self.fields["section"].initial = preferred_section_uuid
            self.preferred_section = next(
                filter(lambda section: section["uuid"] == preferred_section_uuid, sections), None
            )
        if initial := self.instance.data.get("dispatched_section_uuid"):
            self.fields["section"].initial = initial

    def clean(self):
        super().clean()
        if (
            self.cleaned_data["state"] == AbstractParticipation.States.CONFIRMED
            and not self.cleaned_data["section"]
        ):
            self.add_error(
                "section",
                ValidationError(_("You must select a section when confirming a participation.")),
            )

    def save(self, commit=True):
        self.instance.data["dispatched_section_uuid"] = self.cleaned_data["section"]
        super().save(commit)


DispositionParticipationFormset = forms.modelformset_factory(
    model=AbstractParticipation,
    form=DispositionParticipationForm,
    extra=0,
    can_order=False,
    can_delete=True,
)


class AddUserForm(forms.Form):
    user = forms.ModelChoiceField(
        widget=ModelSelect2Widget(
            model=UserProfile,
            search_fields=["first_name__icontains", "last_name__icontains"],
            attrs={"form": "add-user-form"},
        ),
        queryset=UserProfile.objects.none(),  # set using __init__
    )

    def __init__(self, user_queryset, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = user_queryset


class SectionBasedAddUserView(SingleObjectMixin, TemplateResponseMixin, View):
    template_name = "basesignup/section_based/fragment_participant.html"
    model = Shift
    form_class = AddUserForm

    def post(self, request, *args, **kwargs):
        shift = self.get_object()
        form = AddUserForm(
            user_queryset=UserProfile.objects.exclude(localparticipation__shift__in=[shift]),
            data=request.POST,
        )
        if form.is_valid():
            user: UserProfile = form.cleaned_data["user"]
            return self.render_to_response(
                {
                    "form": DispositionParticipationForm(
                        instance=shift.signup_method.get_participation_for(user.as_participant()),
                        shift=shift,
                    ),
                }
            )
        raise Http404("User does not exist")


class SectionBasedDispositionView(CustomPermissionRequiredMixin, SingleObjectMixin, TemplateView):
    # TODO unite this class with the request_confirm one ;)
    model = Shift
    permission_required = "event_management.change_event"
    template_name = "basesignup/disposition.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.object: Shift = self.get_object()

    def get_permission_object(self):
        return self.object.event

    def get_formset(self):
        formset = DispositionParticipationFormset(
            self.request.POST or None,
            queryset=self.object.participations,
            prefix="participations",
            form_kwargs=dict(shift=self.object),
        )
        return formset

    def post(self, request, *args, **kwargs):
        formset = self.get_formset()
        if formset.is_valid():
            formset.save()
            return redirect(self.object.event.get_absolute_url())
        return self.get(request, *args, **kwargs, formset=formset)

    def get_context_data(self, **kwargs):
        kwargs.setdefault("formset", self.get_formset())
        kwargs.setdefault("states", AbstractParticipation.States)
        kwargs.setdefault("sections", self.object.signup_method.configuration.sections)
        kwargs.setdefault(
            "participant_template", "basesignup/section_based/fragment_participant.html"
        )
        kwargs.setdefault(
            "add_user_form",
            AddUserForm(
                user_queryset=UserProfile.objects.exclude(
                    localparticipation__shift__in=[self.object]
                )
            ),
        )
        return super().get_context_data(**kwargs)


class SectionForm(forms.Form):
    title = forms.CharField(label=_("Title"), required=True)
    qualifications = forms.ModelMultipleChoiceField(
        label=_("Required Qualifications"),
        queryset=Qualification.objects.all(),
        widget=Select2MultipleWidget,
        required=False,
    )
    min_count = forms.IntegerField(label=_("min amount"), min_value=0, required=True)
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
        required=False,
        # choices are set as (uuid, title) of section
    )


class SectionBasedSignupView(FormView, BaseSignupView):
    template_name = "basesignup/section_based/signup.html"

    @cached_property
    def sections_participant_qualifies_for(self):
        return sections_participant_qualifies_for(
            self.method.configuration.sections, self.request.user.as_participant()
        )

    def get_form(self, form_class=None):
        form = SectionSignupForm(self.request.POST)
        form.fields["section"].choices = [
            (section["uuid"], section["title"])
            for section in self.sections_participant_qualifies_for
        ]
        return form

    def get_context_data(self, **kwargs):
        kwargs.setdefault("shift", self.shift)
        kwargs.setdefault(
            "unqualified_sections",
            [
                section["title"]
                for section in self.method.configuration.sections
                if section not in self.sections_participant_qualifies_for
            ],
        )
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        return super().signup_pressed(preferred_section_uuid=form.cleaned_data.get("section"))

    def signup_pressed(self):
        if not self.method.configuration.choose_preferred_section:
            # do straight signup if choosing is not enabled
            return super().signup_pressed()

        if not self.method.can_sign_up(self.request.user.as_participant()):
            # redirect a misled request
            messages.warning(self.request, _("You can not sign up for this shift."))
            return redirect(
                reverse("event_management:event_detail", kwargs=dict(pk=self.shift.event_id))
            )

        # all good, redirect to the form
        return redirect(reverse("event_management:signup_action", kwargs=dict(pk=self.shift.pk)))


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

    @staticmethod
    def check_qualification(method, participant):
        if not sections_participant_qualifies_for(method.configuration.sections, participant):
            return ParticipationError(_("You are not qualified."))

    @property
    def signup_checkers(self):
        return super().signup_checkers + [self.check_qualification]

    def perform_signup(self, participant: AbstractParticipant, preferred_section_uuid=None):
        participation = super().perform_signup(participant)
        participation.data["preferred_section_uuid"] = preferred_section_uuid
        if preferred_section_uuid:
            # reset dispatch decision, as that would have overwritten the preferred choice
            participation.data["dispatched_section_uuid"] = None
        participation.state = AbstractParticipation.States.REQUESTED
        participation.save()

    def render_configuration_form(self, *args, form=None, **kwargs):
        form = form or self.get_configuration_form(*args, **kwargs)
        template = get_template("basesignup/section_based/configuration_form.html").render(
            {"form": form}
        )
        return template

    def render_shift_state(self, request):
        section_by_uuid = {section["uuid"]: section for section in self.configuration.sections}
        # get name and preferred section uuid for confirmed participants
        # if they have a section assigned and we have that section on record
        confirmed_participations = [
            {
                "name": str(participation.participant),
                "uuid": dispatched_section_uuid,
            }
            for participation in self.shift.participations.filter(
                state=AbstractParticipation.States.CONFIRMED
            )
            if (dispatched_section_uuid := participation.data.get("dispatched_section_uuid"))
            and dispatched_section_uuid in section_by_uuid
        ]
        # group by section and do some stats
        confirmed_sections_with_users = [
            (section_by_uuid.get(uuid), [user["name"] for user in group])
            for uuid, group in groupby(
                sorted(confirmed_participations, key=itemgetter("uuid")), itemgetter("uuid")
            )
        ]

        return get_template("basesignup/section_based/fragment_state.html").render(
            {
                "shift": self.shift,
                "requested_participations": (
                    self.shift.participations.filter(state=AbstractParticipation.States.REQUESTED)
                ),
                "confirmed_sections_with_users": confirmed_sections_with_users,
                "disposition_url": (
                    reverse(
                        "basesignup:shift_disposition_section_based",
                        kwargs=dict(pk=self.shift.pk),
                    )
                    if request.user.has_perm("event_management.change_event", obj=self.shift.event)
                    else None
                ),
            }
        )
