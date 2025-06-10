from django import forms
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django_select2.forms import Select2MultipleWidget, Select2Widget
from rest_framework import serializers

from ephios.core.models.events import AbstractParticipation
from ephios.core.signup.forms import AdditionalField
from ephios.core.signup.participants import AbstractParticipant, LocalUserParticipant


class Question(models.Model):
    class Type(models.TextChoices):
        TEXT = "text", _("Text input")
        SINGLE_RADIO = "single_radio", _("Single choice")
        SINGLE_LIST = "single_list", _("Single choice (list)")
        MULTIPLE = "multiple", _("Multiple choice")

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
        max_length=20, verbose_name=_("Type"), choices=Type.choices, default=Type.TEXT
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
        if (
            self.type in [self.Type.SINGLE_RADIO, self.Type.SINGLE_LIST, self.Type.MULTIPLE]
            and initial not in self.choices
        ):
            initial = None

        field_name = self.get_form_slug()
        required = self.required if initial is not None else False

        form_class = None
        form_kwargs = {
            "label": self.question_text,
            "help_text": self.description,
            "initial": initial,
            "required": required,
        }

        serializer_class = None
        serializer_kwargs = {
            "required": required,
        }

        match self.type:
            case self.Type.TEXT:
                form_class = forms.CharField
                serializer_class = serializers.CharField
            case self.Type.SINGLE_RADIO:
                form_class = forms.ChoiceField
                serializer_class = serializers.ChoiceField
                form_kwargs["widget"] = forms.RadioSelect
            case self.Type.SINGLE_LIST:
                form_class = forms.ChoiceField
                serializer_class = serializers.ChoiceField
                form_kwargs["widget"] = Select2Widget
            case self.Type.MULTIPLE:
                form_class = forms.MultipleChoiceField
                serializer_class = serializers.MultipleChoiceField
                form_kwargs["widget"] = Select2MultipleWidget

        if self.type != self.Type.TEXT:
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

    def get_form_slug(self):
        return slugify(f"{self.pk} {self.name}")

    @staticmethod
    def get_pk_from_slug(slug: str):
        return slug.split(".", maxsplit=1)[1].split("-")[0]
