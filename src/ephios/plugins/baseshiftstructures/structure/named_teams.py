import uuid
from collections import Counter, defaultdict
from itertools import groupby
from operator import itemgetter

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext_lazy
from rest_framework import serializers

from ephios.core.models import AbstractParticipation, Qualification
from ephios.core.signup.disposition import BaseDispositionParticipationForm
from ephios.core.signup.flow.participant_validation import ParticipantUnfitError
from ephios.core.signup.forms import SignupForm
from ephios.core.signup.participants import AbstractParticipant
from ephios.plugins.baseshiftstructures.structure.group_common import (
    AbstractGroupBasedStructureConfigurationForm,
    BaseGroupBasedShiftStructure,
    QualificationRequirementForm,
    format_min_max_count,
)


def teams_participant_qualifies_for(teams, participant: AbstractParticipant):
    available_qualification_ids = set(q.id for q in participant.collect_all_qualifications())
    return [
        team
        for team in teams
        if not (q := team.get("qualification")) or q in available_qualification_ids
    ]


class NamedTeamsDispositionParticipationForm(BaseDispositionParticipationForm):
    disposition_participation_template = (
        "baseshiftstructures/named_teams/fragment_participation.html"
    )

    team = forms.ChoiceField(
        label=_("Section"),
        required=False,  # only required if participation is confirmed
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        teams = self.shift.structure.configuration.teams
        qualified_teams = list(
            teams_participant_qualifies_for(
                teams,
                self.instance.participant,
            )
        )
        unqualified_teams = [team for team in teams if team not in qualified_teams]
        self.fields["team"].choices = [("", "---")]
        if qualified_teams:
            self.fields["team"].choices += [
                (
                    _("qualified"),
                    [(team["uuid"], team["title"]) for team in qualified_teams],
                )
            ]
        if unqualified_teams:
            self.fields["team"].choices += [
                (
                    _("unqualified"),
                    [(team["uuid"], team["title"]) for team in unqualified_teams],
                )
            ]
        if preferred_team_uuid := self.instance.structure_data.get("preferred_team_uuid"):
            self.fields["team"].initial = preferred_team_uuid
            self.preferred_team = next(
                filter(lambda team: team["uuid"] == preferred_team_uuid, teams), None
            )
        if initial := self.instance.structure_data.get("dispatched_team_uuid"):
            self.fields["team"].initial = initial

    def clean(self):
        super().clean()
        if (
            self.cleaned_data["state"] == AbstractParticipation.States.CONFIRMED
            and not self.cleaned_data["team"]
        ):
            self.add_error(
                "team",
                ValidationError(_("You must select a team when confirming a participation.")),
            )

    def save(self, commit=True):
        self.instance.structure_data["dispatched_team_uuid"] = self.cleaned_data["team"]
        super().save(commit)


class NamedTeamForm(QualificationRequirementForm):
    title = forms.CharField(label=_("Title"), required=True)
    uuid = forms.CharField(widget=forms.HiddenInput, required=False)

    def clean_uuid(self):
        return self.cleaned_data.get("uuid") or uuid.uuid4()


NamedTeamsFormset = forms.formset_factory(
    NamedTeamForm, can_delete=True, min_num=1, validate_min=1, extra=0
)


class NamedTeamsConfigurationForm(AbstractGroupBasedStructureConfigurationForm):
    template_name = "baseshiftstructures/named_teams/configuration_form.html"
    choose_preferred_team = forms.BooleanField(
        label=_("Participants must provide a preferred team"),
        help_text=_(
            "Participants will be asked during signup. This only makes sense if you configure multiple teams."
        ),
        widget=forms.CheckboxInput,
        required=False,
        initial=False,
    )
    teams = forms.Field(
        label=_("Teams"),
        widget=forms.HiddenInput,
        required=False,
    )
    formset_data_field_name = "teams"

    def get_formset_class(self):
        return NamedTeamsFormset

    @classmethod
    def format_formset_item(cls, item):
        return item["title"]


class NamedTeamsShiftStructure(BaseGroupBasedShiftStructure):
    slug = "named_teams"
    verbose_name = _("Named teams")
    description = _("Define named teams of participants with different requirements.")
    configuration_form_class = NamedTeamsConfigurationForm
    shift_state_template_name = "baseshiftstructures/named_teams/fragment_state.html"
    disposition_participation_form_class = NamedTeamsDispositionParticipationForm

    NO_TEAM_UUID = "noteam"

    def _choose_team_for_participation(self, participation):
        return participation.structure_data.get(
            "dispatched_team_uuid"
        ) or participation.structure_data.get("preferred_team_uuid")

    def _get_signup_stats_per_group(self, participations):
        from ephios.core.signup.stats import SignupStats

        confirmed_counter = Counter()
        requested_counter = Counter()
        for p in participations:
            if p.state == AbstractParticipation.States.CONFIRMED:
                c = confirmed_counter
            elif p.state == AbstractParticipation.States.REQUESTED:
                c = requested_counter
            else:
                continue
            team_uuid = self._choose_team_for_participation(p)
            if not team_uuid or team_uuid not in (
                team["uuid"] for team in self.configuration.teams
            ):
                team_uuid = self.NO_TEAM_UUID
            c[team_uuid] += 1

        d = {}
        for team in self.configuration.teams:
            team_uuid = team["uuid"]
            min_count = team.get("min_count")
            max_count = team.get("max_count")
            d[team_uuid] = SignupStats(
                requested_count=requested_counter[team_uuid],
                confirmed_count=confirmed_counter[team_uuid],
                missing=(max(min_count - confirmed_counter[team_uuid], 0) if min_count else 0),
                free=(max(max_count - confirmed_counter[team_uuid], 0) if max_count else None),
                min_count=min_count,
                max_count=max_count,
            )

        # Participations not assigned to a team are extra, so max and free are explicitly zero.
        # We do not offset missing places in other teams, as qualifications etc. might not match.
        # Disposition will always be required to resolve unassigned participations.
        d[self.NO_TEAM_UUID] = SignupStats(
            requested_count=requested_counter[self.NO_TEAM_UUID],
            confirmed_count=confirmed_counter[self.NO_TEAM_UUID],
            missing=0,
            free=0,
            min_count=None,
            max_count=0,
        )

        return d

    def get_checkers(self):
        def check_qualifications_and_max_count(shift, participant):
            viable_teams = teams_participant_qualifies_for(
                shift.structure.configuration.teams, participant
            )
            if not viable_teams:
                raise ParticipantUnfitError(_("You are not qualified."))

            # check if teams are full if signup flow does not use requested state
            if shift.signup_flow.uses_requested_state:
                return
            free_team = False
            team_stats = self._get_signup_stats_per_group(self.shift.participations.all())
            for team in viable_teams:
                if team_stats[team["uuid"]].has_free():
                    free_team = True
                    break
            if not free_team:
                raise ParticipantUnfitError(_("All teams you qualify for are full."))

        return super().get_checkers() + [check_qualifications_and_max_count]

    def _configure_participation(
        self, participation: AbstractParticipation, **kwargs
    ) -> AbstractParticipation:
        participation.state = AbstractParticipation.States.REQUESTED
        return participation

    def get_shift_state_context_data(self, request, **kwargs):
        context_data = super().get_shift_state_context_data(request)
        participations = context_data["participations"]
        teams_stats = self._get_signup_stats_per_group(participations)
        teams = {}
        for team in self.configuration.teams:
            try:
                qualification = Qualification.objects.get(id=team["qualification"])
            except Qualification.DoesNotExist:
                qualification = None
            teams[team["uuid"]] = {
                "title": team["title"],
                "placeholder": team.get("min_count") or 0,
                "qualification_label": qualification.abbreviation if qualification else "",
                "min_max_count": format_min_max_count(team.get("min_count"), team.get("max_count")),
                "participations": [],
                "stats": teams_stats[team["uuid"]],
            }

        unsorted_participations = []
        for participation in participations:
            dispatched_uuid = self._choose_team_for_participation(participation)
            if dispatched_uuid not in teams:
                unsorted_participations.append(participation)
            else:
                teams[dispatched_uuid]["participations"].append(participation)
                teams[dispatched_uuid]["placeholder"] -= 1

        for team in teams.values():
            team["placeholder"] = list(range(max(0, team["placeholder"])))
        if unsorted_participations:
            teams[self.NO_TEAM_UUID] = {
                "title": _("unassigned"),
                "participations": unsorted_participations,
                "placeholder": [],
                "stats": teams_stats[self.NO_TEAM_UUID],
            }

        context_data["teams"] = teams
        return context_data

    def _get_teams_with_users(self):
        team_by_uuid = {team["uuid"]: team for team in self.configuration.teams}
        # get name and preferred team uuid for confirmed participants
        # if they have a team assigned and we have that team on record
        confirmed_participations = [
            {
                "name": str(participation.participant),
                "relevant_qualifications": ", ".join(
                    participation.participant.qualifications
                    .filter(
                        category__show_with_user=True,
                    )
                    .order_by("category", "abbreviation")
                    .values_list("abbreviation", flat=True)
                ),
                "uuid": dispatched_team_uuid,
            }
            for participation in self.shift.participations.filter(
                state=AbstractParticipation.States.CONFIRMED
            )
            if (dispatched_team_uuid := participation.structure_data.get("dispatched_team_uuid"))
            and dispatched_team_uuid in team_by_uuid
        ]
        # group by team and do some stats
        teams_with_users = [
            (
                team_by_uuid.pop(uuid),
                [[user["name"], user["relevant_qualifications"]] for user in group],
            )
            for uuid, group in groupby(
                sorted(confirmed_participations, key=itemgetter("uuid")), itemgetter("uuid")
            )
        ]
        # add teams without participants
        teams_with_users += [(team, None) for team in team_by_uuid.values()]
        return teams_with_users

    def get_list_export_data(self):
        export_data = []
        team_by_uuid = {team["uuid"]: team for team in self.configuration.teams}

        participants_by_team_uuid = defaultdict(list)
        for p in self.shift.participations.all():
            participant_team_uuid = self._choose_team_for_participation(p)
            participants_by_team_uuid[
                participant_team_uuid or NamedTeamsShiftStructure.NO_TEAM_UUID
            ].append(p)

        for team_uuid, team in team_by_uuid.items():
            missing_count = team["min_count"]
            team_qualifications = (
                Qualification.objects.filter(id=team["qualification"]) if team else []
            )
            for p in participants_by_team_uuid[team_uuid]:
                if p.state in AbstractParticipation.States.REQUESTED_AND_CONFIRMED:
                    missing_count -= 1
                export_data.append({
                    "participation": p,
                    "required_qualifications": team_qualifications,
                    "description": team["title"] if team else "",
                })
            # fill up team with empty slots
            for __ in range(missing_count):
                export_data.append({
                    "participation": None,
                    "required_qualifications": team_qualifications,
                    "description": team["title"] if team else "",
                })

        # unassigned participations
        for p in participants_by_team_uuid[NamedTeamsShiftStructure.NO_TEAM_UUID]:
            export_data.append({
                "participation": p,
                "required_qualifications": [],
                "description": "",
            })

        return export_data

    def get_signup_form_fields(self, participant, participation, signup_choice):
        team_stats = self._get_signup_stats_per_group(self.shift.participations.all())
        enabled_teams = []
        not_qualified_teams = []
        full_teams = []
        for team in self.shift.structure.configuration.teams:
            if team["uuid"] in [
                participation.structure_data.get("preferred_team_uuid"),
                participation.structure_data.get("dispatched_team_uuid"),
            ]:
                enabled_teams.append(team)
            elif team not in teams_participant_qualifies_for(
                self.shift.structure.configuration.teams, participant
            ):
                not_qualified_teams.append(team)
            elif (
                not self.shift.signup_flow.uses_requested_state
                and not team_stats[team["uuid"]].has_free()
            ):
                full_teams.append(team)
            else:
                enabled_teams.append(team)

        initial = participation.structure_data.get("preferred_team_uuid")
        required = (
            signup_choice != SignupForm.SignupChoices.DECLINE
            and self.shift.structure.configuration.choose_preferred_team
        )
        choices = [(team["uuid"], team["title"]) for team in enabled_teams]

        help_text = ""
        if not_qualified_teams:
            help_text = _("You don't qualify for {teams}.").format(
                teams=", ".join(str(team["title"]) for team in not_qualified_teams)
            )
        if full_teams:
            help_text += " " + ngettext_lazy(
                "{teams} is full.", "{teams} are full.", len(full_teams)
            ).format(teams=", ".join(str(team["title"]) for team in full_teams))

        return {
            "baseshiftstructures_named_teams_preferred_team_uuid": {
                "label": _("Preferred Team"),
                "help_text": help_text,
                "default": initial,
                "required": required,
                "form_class": forms.ChoiceField,
                "form_kwargs": {
                    "choices": choices,
                    "widget": forms.RadioSelect,
                },
                "serializer_class": serializers.ChoiceField,
                "serializer_kwargs": {
                    "choices": choices,
                },
            },
        }

    def save_signup(self, participant, participation, signup_choice, cleaned_data):
        if signup_choice != SignupForm.SignupChoices.DECLINE:
            participation.structure_data["preferred_team_uuid"] = cleaned_data[
                "baseshiftstructures_named_teams_preferred_team_uuid"
            ]
            participation.save(update_fields=["structure_data"])
