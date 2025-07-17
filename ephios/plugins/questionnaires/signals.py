from django import forms
from django.dispatch import receiver
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ephios.core.models.events import AbstractParticipation, Shift
from ephios.core.signals import (
    nav_link,
    register_group_permission_fields,
    shift_copy,
    shift_forms,
    signup_form_fields,
    signup_save,
)
from ephios.core.signup.forms import SignupForm
from ephios.core.signup.participants import AbstractParticipant, LocalUserParticipant
from ephios.extra.permissions import PermissionField
from ephios.plugins.questionnaires.forms import QuestionnaireForm
from ephios.plugins.questionnaires.models import Answer, Question, Questionnaire, SavedAnswer


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


@receiver(shift_copy, dispatch_uid="ephios.plugins.questionnaires.signals.shift_copy")
def copy_shift_questionnaire(sender, shift: Shift, copies: list[Shift], **kwargs):
    if hasattr(shift, "questionnaire") and shift.questionnaire:
        questions = shift.questionnaire.questions.all()

        for copy in copies:
            questionnaire = Questionnaire.objects.create(shift=copy)
            questionnaire.questions.set(questions)


@receiver(shift_forms, dispatch_uid="ephios.plugins.questionnaires.signals.shift_forms")
def question_selection_form(sender, shift, request, **kwargs):
    return [QuestionnaireForm(request.POST or None, shift=shift)]


@receiver(
    signup_form_fields, dispatch_uid="ephios.plugins.questionnaires.signals.signup_form_fields"
)
def provide_signup_form_fields(
    sender,
    shift: Shift,
    participant: AbstractParticipant,
    participation: AbstractParticipation,
    signup_choice,
    **kwargs
):
    if signup_choice == SignupForm.SignupChoices.DECLINE:
        return None

    questions = (
        shift.questionnaire.questions.all()
        if hasattr(shift, "questionnaire") and shift.questionnaire
        else []
    )
    formfields = dict(
        question.get_signup_form_field(participant, participation, signup_choice)
        for question in questions
    )

    if len(formfields) > 0:
        can_save_answers = isinstance(participant, LocalUserParticipant)
        formfields["questionnaires_save_answers"] = {
            "form_class": forms.BooleanField,
            "form_kwargs": {
                "label": _("Save answers to my user profile for future sign-ups"),
                "initial": can_save_answers,
                "disabled": not can_save_answers,
                "required": False,
                "widget": forms.HiddenInput if not can_save_answers else forms.CheckboxInput,
            },
            "serializer_class": serializers.BooleanField,
            "serializer_kwargs": {
                "disabled": not can_save_answers,
                "required": False,
            },
        }

    return formfields


@receiver(signup_save, dispatch_uid="ephios.plugins.questionnaires.signals.signup_save")
def save_signup(
    sender,
    shift: Shift,
    participant: AbstractParticipant,
    participation: AbstractParticipation,
    cleaned_data,
    **kwargs
):
    save_answers = cleaned_data.get("questionnaires_save_answers")
    if save_answers:
        assert isinstance(
            participant, LocalUserParticipant
        ), "Cannot save answers, participant is not a local user"

    for name, value in cleaned_data.items():
        if name == "questionnaires_save_answers" or not name.startswith("questionnaires_"):
            continue

        answer, _ = Answer.objects.get_or_create(
            participation=participation, question_id=Question.get_pk_from_slug(name)
        )
        answer.answer = value
        answer.save()

        if save_answers:
            saved_answer, _ = SavedAnswer.objects.get_or_create(
                user=participant.user, question_id=Question.get_pk_from_slug(name)
            )
            saved_answer.answer = value
            saved_answer.save()
