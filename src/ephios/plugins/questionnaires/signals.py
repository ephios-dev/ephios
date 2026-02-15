from django import forms
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ephios.core.models.events import AbstractParticipation, Shift
from ephios.core.signals import (
    HTML_DISPOSITION_PARTICIPATION,
    insert_html,
    nav_link,
    register_group_permission_fields,
    settings_sections,
    shift_action,
    shift_copy,
    shift_forms,
    signup_form_fields,
    signup_save,
)
from ephios.core.signup.forms import SignupForm
from ephios.core.signup.participants import AbstractParticipant, LocalUserParticipant
from ephios.core.views.settings import SETTINGS_PERSONAL_SECTION_KEY
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


@receiver(settings_sections, dispatch_uid="ephios.plugins.questionnaires.signals.settings_sections")
def add_settings_section(sender, request, **kwargs):
    return [
        {
            "label": _("Saved answers"),
            "url": reverse_lazy("questionnaires:saved_answer_list"),
            "active": request.resolver_match
            and request.resolver_match.app_name == "questionnaires"
            and request.resolver_match.url_name == "saved_answer_list",
            "group": SETTINGS_PERSONAL_SECTION_KEY,
        }
    ]


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
    **kwargs,
):
    if signup_choice == SignupForm.SignupChoices.DECLINE:
        return {}

    questions = (
        shift.questionnaire.questions.all()
        if hasattr(shift, "questionnaire") and shift.questionnaire
        else []
    )
    formfields = dict(
        question.get_signup_form_field(participant, participation) for question in questions
    )

    if any(q.use_saved_answers for q in questions) and isinstance(
        participant, LocalUserParticipant
    ):
        formfields["questionnaires_save_answers"] = {
            "label": _("Save answers to my user profile for future sign-ups"),
            "default": True,
            "required": False,
            "form_class": forms.BooleanField,
            "form_kwargs": {},
            "serializer_class": serializers.BooleanField,
            "serializer_kwargs": {},
        }

    return formfields


@receiver(signup_save, dispatch_uid="ephios.plugins.questionnaires.signals.signup_save")
def save_signup(
    sender,
    shift: Shift,
    participant: AbstractParticipant,
    participation: AbstractParticipation,
    signup_choice,
    cleaned_data,
    **kwargs,
):
    if signup_choice == SignupForm.SignupChoices.DECLINE:
        return

    save_answers = (
        cleaned_data.get("questionnaires_save_answers", False)
        if isinstance(participant, LocalUserParticipant)
        else False
    )

    for name, value in cleaned_data.items():
        if name == "questionnaires_save_answers" or not name.startswith("questionnaires_"):
            continue
        question = Question.objects.get(pk=Question.get_pk_from_slug(name))

        if value:
            Answer.objects.update_or_create(
                participation=participation,
                question=question,
                defaults={"answer": value},
            )

            if save_answers and question.use_saved_answers:
                SavedAnswer.objects.update_or_create(
                    user=participant.user,
                    question_id=Question.get_pk_from_slug(name),
                    defaults={"answer": value},
                )
        else:
            Answer.objects.filter(
                participation=participation, question_id=Question.get_pk_from_slug(name)
            ).delete()

            if save_answers and question.use_saved_answers:
                SavedAnswer.objects.filter(
                    user=participant.user, question_id=Question.get_pk_from_slug(name)
                ).delete()


@receiver(
    insert_html,
    sender=HTML_DISPOSITION_PARTICIPATION,
    dispatch_uid="ephios.plugins.questionnaires.signals.insert_html",
)
def disposition_render_responses(request, participation: AbstractParticipation, **kwargs):
    answers = participation.answer_set.all()

    if not answers:
        return ""

    return render_to_string(
        "questionnaires/disposition_participation_answers.html", {"answers": answers}
    )


@receiver(shift_action, dispatch_uid="ephios.plugins.questionnaires.signals.shift_action")
def add_shift_action(sender, shift: Shift, request, **kwargs):
    if hasattr(shift, "questionnaire") and shift.questionnaire and shift.questionnaire.questions:
        return [
            {
                "label": _("View answers"),
                "url": reverse_lazy("questionnaires:shift_aggregate_answers", args=(shift.pk,)),
            }
        ]

    return []
