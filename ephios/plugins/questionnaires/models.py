from django import forms
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ephios.core.models.events import AbstractParticipation
from ephios.core.signup.forms import AdditionalField
from ephios.core.signup.participants import AbstractParticipant, LocalUserParticipant


class Question(models.Model):
    TYPE_TEXT = "text"
    TYPE_SINGLE_RADIO = "single_radio"
    TYPE_SINGLE_LIST = "single_list"
    TYPE_MULTIPLE = "multiple"
    TYPE_CHOICES = [
        (TYPE_TEXT, _("Text input")),
        (TYPE_SINGLE_RADIO, _("Single choice")),
        (TYPE_SINGLE_LIST, _("Single choice (list)")),
        (TYPE_MULTIPLE, _("Multiple choice")),
    ]

    name = models.CharField(
        max_length=50,
        verbose_name=_("Name"),
        help_text=_(
            "The name of the question is used to identify the question, for example when picking questions for a shift"
        ),
    )
    question_text = models.CharField(max_length=100, verbose_name=_("Question"))
    description = models.TextField(verbose_name=_("Description"), blank=True, null=True)
    required = models.BooleanField(
        verbose_name=_("Required"),
        help_text=_("Whether users must submit an answer to this question"),
    )
    type = models.CharField(
        max_length=20, verbose_name=_("Type"), choices=TYPE_CHOICES, default=TYPE_TEXT
    )
    choices = models.JSONField(default=list, verbose_name=_("Choices"))

    class Meta:
        verbose_name = _("Question")
        verbose_name_plural = _("Questions")

    def __str__(self):
        # pylint: disable=invalid-str-returned
        return self.name

    def get_signup_formfield(
        self, participant: AbstractParticipant, participation: AbstractParticipation, signup_choice
    ):
        # Restore answer from participation (when editing) or the user's saved answers (if local participant)
        answer_key = str(self.pk)
        if answer_key in participation.questionnaire_answers:
            initial = participation.questionnaire_answers[answer_key]
        elif (
            isinstance(participant, LocalUserParticipant)
            and answer_key in participant.user.saved_questionnaire_answers
        ):
            initial = participant.user.saved_questionnaire_answers[answer_key]
        else:
            initial = None

        # Reset answer if selected option does not exist
        if self.type != self.TYPE_TEXT and initial not in self.choices:
            initial = None

        field_name = slugify(f"{self.pk} {self.name}")
        required = self.required if initial is not None else False

        form_class = (
            forms.CharField
            if self.type == self.TYPE_TEXT
            else (
                forms.MultipleChoiceField if self.type == self.TYPE_MULTIPLE else forms.ChoiceField
            )
        )
        form_kwargs = {
            "label": self.question_text,
            "help_text": self.description,
            "initial": initial,
            "required": required,
        }
        if self.type == self.TYPE_SINGLE_RADIO:
            form_kwargs["widget"] = forms.RadioSelect

        serializer_class = (
            serializers.CharField
            if self.type == self.TYPE_TEXT
            else (
                serializers.MultipleChoiceField
                if self.type == self.TYPE_MULTIPLE
                else serializers.ChoiceField
            )
        )
        serializer_kwargs = {
            "required": required,
        }

        if self.type != self.TYPE_TEXT:
            assert isinstance(
                self.choices, list
            ), f"The choices of question {self.name} are not a list"
            # pylint: disable=not-an-iterable
            choices = [(choice, choice) for choice in self.choices]
            form_kwargs["choices"] = choices
            serializer_kwargs["choices"] = choices

        return AdditionalField(
            field_name, form_class, form_kwargs, serializer_class, serializer_kwargs
        )
