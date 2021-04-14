import uuid
from functools import cached_property
from itertools import groupby
from operator import itemgetter

from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.template.loader import get_template
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from django_select2.forms import Select2MultipleWidget
from dynamic_preferences.registries import global_preferences_registry

from ephios.core.models import AbstractParticipation, Qualification
from ephios.core.signup import (
    AbstractParticipant,
    BaseDispositionParticipationForm,
    BaseSignupMethod,
    BaseSignupView,
    ParticipationError,
)


def sections_participant_qualifies_for(sections, participant: AbstractParticipant):
    available_qualification_ids = set(q.id for q in participant.collect_all_qualifications())
    return [
        section
        for section in sections
        if set(section["qualifications"]) <= available_qualification_ids
    ]


class SectionBasedDispositionParticipationForm(BaseDispositionParticipationForm):
    disposition_participation_template = "basesignup/section_based/fragment_participant.html"

    section = forms.ChoiceField(
        label=_("Section"),
        required=False,  # only required if participation is confirmed
        widget=forms.Select(
            attrs={"data-show-for-state": str(AbstractParticipation.States.CONFIRMED)}
        ),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        sections = self.shift.signup_method.configuration.sections
        qualified_sections = list(
            sections_participant_qualifies_for(
                sections,
                self.instance.participant,
            )
        )
        unqualified_sections = [
            section for section in sections if section not in qualified_sections
        ]
        self.fields["section"].choices = [("", "---")]
        if qualified_sections:
            self.fields["section"].choices += [
                (
                    _("qualified"),
                    [(section["uuid"], section["title"]) for section in qualified_sections],
                )
            ]
        if unqualified_sections:
            self.fields["section"].choices += [
                (
                    _("unqualified"),
                    [(section["uuid"], section["title"]) for section in unqualified_sections],
                )
            ]
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
            if not form.cleaned_data.get("DELETE")
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
            self.method.configuration.sections, self.participant
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

    def signup_pressed(self, **kwargs):
        if not self.method.configuration.choose_preferred_section:
            # do straight signup if choosing is not enabled
            return super().signup_pressed(**kwargs)

        if not self.method.can_sign_up(self.participant):
            # redirect a misled request
            messages.warning(self.request, _("You can not sign up for this shift."))
            return redirect(self.participant.reverse_event_detail(self.shift.event))

        # all good, redirect to the form
        return redirect(self.participant.reverse_signup_action(self.shift))


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

    disposition_participation_form_class = SectionBasedDispositionParticipationForm

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

    def get_participant_count_bounds(self):
        return sum(section.get("min_count") or 0 for section in self.configuration.sections), None

    @staticmethod
    def check_qualification(method, participant):
        if not sections_participant_qualifies_for(method.configuration.sections, participant):
            return ParticipationError(_("You are not qualified."))

    @property
    def _signup_checkers(self):
        return super()._signup_checkers + [self.check_qualification]

    # pylint: disable=arguments-differ
    def _configure_participation(
        self, participation: AbstractParticipation, preferred_section_uuid=None, **kwargs
    ) -> AbstractParticipation:
        participation.data["preferred_section_uuid"] = preferred_section_uuid
        if preferred_section_uuid:
            # reset dispatch decision, as that would have overwritten the preferred choice
            participation.data["dispatched_section_uuid"] = None
        participation.state = AbstractParticipation.States.REQUESTED
        return participation

    def render_configuration_form(self, *args, form=None, **kwargs):
        form = form or self.get_configuration_form(*args, **kwargs)
        template = get_template("basesignup/section_based/configuration_form.html").render(
            {"form": form}
        )
        return template

    def _get_sections_with_users(self):
        relevant_qualification_categories = global_preferences_registry.manager()[
            "general__relevant_qualification_categories"
        ]
        section_by_uuid = {section["uuid"]: section for section in self.configuration.sections}
        # get name and preferred section uuid for confirmed participants
        # if they have a section assigned and we have that section on record
        confirmed_participations = [
            {
                "name": str(participation.participant),
                "relevant_qualifications": ", ".join(
                    participation.participant.qualifications.filter(
                        category__in=relevant_qualification_categories
                    )
                    .order_by("category", "abbreviation")
                    .values_list("abbreviation", flat=True)
                ),
                "uuid": dispatched_section_uuid,
            }
            for participation in self.shift.participations.filter(
                state=AbstractParticipation.States.CONFIRMED
            )
            if (dispatched_section_uuid := participation.data.get("dispatched_section_uuid"))
            and dispatched_section_uuid in section_by_uuid
        ]
        # group by section and do some stats
        sections_with_users = [
            (
                section_by_uuid.pop(uuid),
                [[user["name"], user["relevant_qualifications"]] for user in group],
            )
            for uuid, group in groupby(
                sorted(confirmed_participations, key=itemgetter("uuid")), itemgetter("uuid")
            )
        ]
        # add sections without participants
        sections_with_users += [(section, None) for section in section_by_uuid.values()]
        return sections_with_users

    def render_shift_state(self, request):
        return get_template("basesignup/section_based/fragment_state.html").render(
            {
                "shift": self.shift,
                "requested_participations": (
                    self.shift.participations.filter(state=AbstractParticipation.States.REQUESTED)
                ),
                "sections_with_users": self._get_sections_with_users(),
                "disposition_url": (
                    reverse(
                        "core:shift_disposition",
                        kwargs=dict(pk=self.shift.pk),
                    )
                    if request.user.has_perm("core.change_event", obj=self.shift.event)
                    else None
                ),
            }
        )

    def get_participation_display(self):
        confirmed_sections_with_users = self._get_sections_with_users()
        participation_display = []
        for section, users in confirmed_sections_with_users:
            if users:
                participation_display += [[user[0], user[1], section["title"]] for user in users]
            if not users or len(users) < section["min_count"]:
                required_qualifications = ", ".join(
                    Qualification.objects.filter(pk__in=section["qualifications"]).values_list(
                        "abbreviation", flat=True
                    )
                )
                participation_display += [["", required_qualifications, section["title"]]] * (
                    section["min_count"] - (len(users) if users else 0)
                )
        return participation_display
