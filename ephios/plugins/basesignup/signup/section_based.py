import uuid
from collections import Counter
from functools import cached_property
from itertools import groupby
from operator import itemgetter

from django import forms
from django.core.exceptions import ValidationError
from django.template.loader import get_template
from django.utils.translation import gettext_lazy as _
from django_select2.forms import Select2MultipleWidget
from dynamic_preferences.registries import global_preferences_registry

from ephios.core.models import AbstractParticipation, Qualification
from ephios.core.signup.disposition import BaseDispositionParticipationForm
from ephios.core.signup.methods import (
    BaseSignupForm,
    BaseSignupMethod,
    BaseSignupView,
    ParticipantUnfitError,
)
from ephios.core.signup.participants import AbstractParticipant

NO_SECTION_UUID = "other"


def sections_participant_qualifies_for(sections, participant: AbstractParticipant):
    available_qualification_ids = set(q.id for q in participant.collect_all_qualifications())
    return [
        section
        for section in sections
        if set(section["qualifications"]) <= available_qualification_ids
    ]


class SectionBasedDispositionParticipationForm(BaseDispositionParticipationForm):
    disposition_participation_template = "basesignup/section_based/fragment_participation.html"

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
    max_count = forms.IntegerField(label=_("max amount"), min_value=1, required=False)
    uuid = forms.CharField(widget=forms.HiddenInput, required=False)

    def clean_uuid(self):
        return self.cleaned_data.get("uuid") or uuid.uuid4()


SectionsFormset = forms.formset_factory(
    SectionForm, can_delete=True, min_num=1, validate_min=1, extra=0
)


class SectionBasedConfigurationForm(BaseSignupMethod.configuration_form_class):
    choose_preferred_section = forms.BooleanField(
        label=_("Participants must provide a preferred section"),
        help_text=_("This only makes sense if you configure multiple sections."),
        widget=forms.CheckboxInput,
        required=False,
        initial=False,
    )
    sections = forms.Field(
        label=_("Structure"),
        widget=forms.HiddenInput,
        required=False,
    )

    def __init__(self, data=None, **kwargs):
        super().__init__(data, **kwargs)
        self.sections_formset = SectionsFormset(
            data=data,
            initial=self.initial.get("sections", []),
            prefix="sections",
        )

    def clean_sections(self):
        if not self.sections_formset.is_valid():
            raise ValidationError(_("The sections aren't configured correctly."))

        sections = [
            {
                key: cleaned_data[key]
                for key in ("title", "qualifications", "min_count", "max_count", "uuid")
            }
            for cleaned_data in self.sections_formset.cleaned_data
            if cleaned_data and not cleaned_data.get("DELETE")
        ]
        return sections

    @staticmethod
    def format_sections(value):
        return ", ".join(section["title"] for section in value)


class SectionSignupForm(BaseSignupForm):
    preferred_section_uuid = forms.ChoiceField(
        label=_("Preferred Section"),
        widget=forms.RadioSelect,
        required=False,
        # choices are later set as (uuid, title) of section
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["preferred_section_uuid"].initial = self.instance.data.get(
            "preferred_section_uuid"
        )
        self.fields["preferred_section_uuid"].required = (
            self.data.get("signup_choice") == "sign_up"
            and self.method.configuration.choose_preferred_section
        )
        self.fields["preferred_section_uuid"].choices = [
            (section["uuid"], section["title"])
            for section in self.sections_participant_qualifies_for
        ]
        unqualified = [
            section
            for section in self.method.configuration.sections
            if section not in self.sections_participant_qualifies_for
        ]
        if unqualified:
            self.fields["preferred_section_uuid"].help_text = _(
                "You don't qualify for {qualifications}."
            ).format(qualifications=", ".join(str(section["title"]) for section in unqualified))

    def save(self, commit=True):
        self.instance.data["preferred_section_uuid"] = self.cleaned_data["preferred_section_uuid"]
        return super().save(commit)

    @cached_property
    def sections_participant_qualifies_for(self):
        return sections_participant_qualifies_for(
            self.method.configuration.sections, self.participant
        )


class SectionBasedSignupView(BaseSignupView):
    form_class = SectionSignupForm


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
    signup_view_class = SectionBasedSignupView
    disposition_participation_form_class = SectionBasedDispositionParticipationForm

    configuration_form_class = SectionBasedConfigurationForm
    shift_state_template_name = "basesignup/section_based/fragment_state.html"

    def _get_signup_stats_per_section(self, participations=None):
        from ephios.core.signup.methods import SignupStats

        if participations is None:
            participations = list(self.shift.participations.all())
        confirmed_counter = Counter()
        requested_counter = Counter()
        for p in participations:
            if p.state == AbstractParticipation.States.CONFIRMED:
                c = confirmed_counter
            elif p.state == AbstractParticipation.States.REQUESTED:
                c = requested_counter
            else:
                continue
            section_uuid = p.data.get("dispatched_section_uuid")
            if not section_uuid or section_uuid not in (
                section["uuid"] for section in self.configuration.sections
            ):
                section_uuid = NO_SECTION_UUID
            c[section_uuid] += 1

        d = {}
        for section in self.configuration.sections:
            section_uuid = section["uuid"]
            min_count = section.get("min_count")
            max_count = section.get("max_count")
            d[section_uuid] = SignupStats(
                requested_count=requested_counter[section_uuid],
                confirmed_count=confirmed_counter[section_uuid],
                missing=(max(min_count - confirmed_counter[section_uuid], 0) if min_count else 0),
                free=(max(max_count - confirmed_counter[section_uuid], 0) if max_count else None),
                min_count=min_count,
                max_count=max_count,
            )

        # Participations not assigned to a section are extra, so max and free are explicitly zero.
        # We do not offset missing places in other sections, as qualifications etc. might not match.
        # Disposition will always be required to resolve unassigned participations.
        d[NO_SECTION_UUID] = SignupStats(
            requested_count=requested_counter[NO_SECTION_UUID],
            confirmed_count=confirmed_counter[NO_SECTION_UUID],
            missing=0,
            free=0,
            min_count=None,
            max_count=0,
        )

        return d

    def get_signup_stats(self):
        from ephios.core.signup.methods import SignupStats

        participations = list(self.shift.participations.all())

        signup_stats = SignupStats.ZERO
        for stats in self._get_signup_stats_per_section(participations).values():
            signup_stats += stats

        return signup_stats

    @staticmethod
    def check_qualification(method, participant):
        if not sections_participant_qualifies_for(method.configuration.sections, participant):
            return ParticipantUnfitError(_("You are not qualified."))

    @property
    def _signup_checkers(self):
        return super()._signup_checkers + [self.check_qualification]

    # pylint: disable=arguments-differ
    def _configure_participation(
        self, participation: AbstractParticipation, **kwargs
    ) -> AbstractParticipation:
        participation.state = AbstractParticipation.States.REQUESTED
        return participation

    def render_configuration_form(self, *args, form=None, **kwargs):
        """We overwrite the template to render the formset."""
        form = form or self.get_configuration_form(*args, **kwargs)
        template = get_template("basesignup/section_based/configuration_form.html").render(
            {"form": form}
        )
        return template

    def get_shift_state_context_data(self, request, **kwargs):
        context_data = super().get_shift_state_context_data(request)
        participations = context_data["participations"]
        section_stats = self._get_signup_stats_per_section(participations)
        sections = {
            section["uuid"]: {
                "title": section["title"],
                "placeholder": section.get("min_count") or 0,
                "qualifications_label": ", ".join(
                    q.abbreviation
                    for q in Qualification.objects.filter(id__in=section["qualifications"])
                ),
                "participations": [],
                "stats": section_stats[section["uuid"]],
            }
            for section in self.configuration.sections
        }

        unsorted_participations = []
        for participation in participations:
            dispatched_uuid = participation.data.get(
                "dispatched_section_uuid"
            ) or participation.data.get("preferred_section_uuid")
            if dispatched_uuid not in sections:
                unsorted_participations.append(participation)
            else:
                sections[dispatched_uuid]["participations"].append(participation)
                sections[dispatched_uuid]["placeholder"] -= 1

        for section in sections.values():
            section["placeholder"] = list(range(max(0, section["placeholder"])))
        if unsorted_participations:
            sections[NO_SECTION_UUID] = {
                "title": _("unassigned"),
                "participations": unsorted_participations,
                "placeholder": [],
            }

        context_data["sections"] = sections
        return context_data

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
