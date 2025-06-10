from django import forms
from django.dispatch import receiver
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ephios.core.models.events import AbstractParticipation, Shift
from ephios.core.signals import (
    nav_link,
    register_group_permission_fields,
    shift_forms,
    signup_formfields,
    signup_save,
)
from ephios.core.signup.forms import AdditionalField, AdditionalFieldList, BaseSignupForm
from ephios.core.signup.participants import AbstractParticipant, LocalUserParticipant
from ephios.extra.permissions import PermissionField
from ephios.plugins.questionnaires.forms import QuestionnaireForm
from ephios.plugins.questionnaires.models import Question


@receiver(nav_link, dispatch_uid="ephios.plugins.questionnaires.signals.nav_link")
def add_nav_link(sender, request, **kwargs):
    return (
        [
            {
                "label": _("Questions"),
                "url": reverse_lazy("questionnaires:question_list"),
                "active": request.resolver_match
                and request.resolver_match.app_name == "questionnaires",
                "group": _("Management"),
            }
        ]
        if request.user.has_perm("questionnaires.view_question")
        else []
    )


@receiver(
    register_group_permission_fields,
    dispatch_uid="ephios.plugins.questionnaires.signals.register_group_permission_fields",
)
def group_permission_fields(sender, **kwargs):
    return [
        (
            "manage_questions",
            PermissionField(
                label=_("Manage Questions"),
                help_text=_("Enables this group to add questions that can be asked during signup."),
                permissions=[
                    "questionnaires.view_question",
                    "questionnaires.add_question",
                    "questionnaires.change_question",
                    "questionnaires.delete_question",
                ],
            ),
        )
    ]


@receiver(shift_forms, dispatch_uid="ephios.plugins.questionnaires.signals.shift_forms")
def question_selection_form(sender, shift, request, **kwargs):
    return [QuestionnaireForm(request.POST or None, shift=shift)]


@receiver(signup_formfields, dispatch_uid="ephios.plugins.questionnaires.signals.signup_formfields")
def provide_signup_formfields(
    sender,
    shift: Shift,
    participant: AbstractParticipant,
    participation: AbstractParticipation,
    signup_choice,
    **kwargs
):
    if signup_choice == BaseSignupForm.SignupChoices.DECLINE:
        return None

    formfields = [
        question.get_signup_formfield(participant, participation, signup_choice)
        for question in Question.objects.filter(pk__in=shift.questionnaire)
    ]

    can_save_answers = isinstance(participant, LocalUserParticipant)
    formfields.append(
        AdditionalField(
            "save_answers",
            forms.BooleanField,
            {
                "label": _("Save answers to my user profile for future sign-ups"),
                "initial": can_save_answers,
                "disabled": not can_save_answers,
                "required": False,
                "widget": forms.HiddenInput if not can_save_answers else forms.CheckboxInput,
            },
            serializers.BooleanField,
            {
                "disabled": not can_save_answers,
                "required": False,
            },
        )
    )

    return (
        AdditionalFieldList(
            "questionnaires",
            {formfield.name: formfield for formfield in formfields},
        )
        if len(formfields) > 0
        else None
    )


@receiver(signup_save, dispatch_uid="ephios.plugins.questionnaires.signals.signup_save")
def save_signup(
    sender,
    shift: Shift,
    participant: AbstractParticipant,
    participation: AbstractParticipation,
    cleaned_data,
    **kwargs
):
    answers = {}

    for name, value in cleaned_data.items():
        if name == "questionnaires.save_answers" or not name.startswith("questionnaires."):
            continue

        # Field name format: questionnaires.123-question-name
        question_pk = Question.get_pk_from_slug(name)
        answers[question_pk] = value

    participation.questionnaire_answers = answers
    participation.save()

    if cleaned_data["questionnaires.save_answers"]:
        assert isinstance(
            participant, LocalUserParticipant
        ), "Cannot save answers, participant is not a local user"
        participant: LocalUserParticipant

        for question, answer in answers.items():
            participant.user.saved_questionnaire_answers[question] = answer

        participant.user.save()
